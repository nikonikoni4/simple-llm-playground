"""
ThreadManager - 线程和节点关系的集中管理器

职责:
1. 维护 thread_id -> thread_view_index 映射 (唯一真实来源)
2. 维护 thread_id -> node_ids 映射
3. 提供线程列表供下拉菜单使用
4. 处理线程重命名
5. 自动删除空线程
"""

from typing import Dict, List, Set, Optional
from PyQt5.QtCore import QObject, pyqtSignal


class ThreadManager(QObject):
    """
    线程和节点关系的集中管理器 (单例)
    
    信号:
        threadsChanged(list): 线程列表变更时发出，参数为线程ID列表
        threadRenamed(str, str): 线程重命名时发出，参数为(old_name, new_name)
        threadDeleted(str): 线程被删除时发出，参数为被删除的thread_id
        viewIndicesChanged(): 线程视图索引变化时发出（用于更新节点Y位置）
    """
    
    # === 信号定义 ===
    threadsChanged = pyqtSignal(list)
    threadRenamed = pyqtSignal(str, str)
    threadDeleted = pyqtSignal(str)
    viewIndicesChanged = pyqtSignal()
    
    # === 单例实现 ===
    _instance: Optional['ThreadManager'] = None
    
    @classmethod
    def instance(cls) -> 'ThreadManager':
        """获取 ThreadManager 单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置单例（主要用于测试）"""
        cls._instance = None
    
    def __init__(self):
        super().__init__()
        # thread_id -> view_index (Y轴位置索引)
        self._thread_to_view_index: Dict[str, int] = {}
        # thread_id -> 该线程包含的节点ID集合
        self._thread_to_nodes: Dict[str, Set[int]] = {}
    
    # ========== 线程查询方法 ==========
    
    def get_all_thread_ids(self) -> List[str]:
        """
        获取所有线程ID列表（供下拉菜单使用）
        
        Returns:
            按 view_index 排序的线程ID列表，main 线程始终在最前
        """
        # 按 view_index 排序
        sorted_threads = sorted(
            self._thread_to_view_index.keys(),
            key=lambda tid: self._thread_to_view_index[tid]
        )
        return sorted_threads
    
    def get_thread_view_index(self, thread_id: str) -> Optional[int]:
        """获取线程的视图索引"""
        return self._thread_to_view_index.get(thread_id)
    
    def get_thread_to_view_index_map(self) -> Dict[str, int]:
        """获取完整的 thread_id -> view_index 映射（用于序列化）"""
        return self._thread_to_view_index.copy()
    
    def thread_exists(self, thread_id: str) -> bool:
        """检查线程是否存在"""
        return thread_id in self._thread_to_view_index
    
    def get_nodes_in_thread(self, thread_id: str) -> Set[int]:
        """获取某个线程中的所有节点ID"""
        return self._thread_to_nodes.get(thread_id, set()).copy()
    
    # ========== 节点-线程关系管理 ==========
    
    def register_node(self, node_id: int, thread_id: str) -> int:
        """
        注册节点到线程
        
        如果线程不存在，会自动创建。
        
        Args:
            node_id: 节点ID
            thread_id: 线程ID
            
        Returns:
            该线程的 view_index
        """
        # 如果线程不存在，创建它
        if thread_id not in self._thread_to_view_index:
            self._create_thread(thread_id)
        
        # 添加节点到线程
        if thread_id not in self._thread_to_nodes:
            self._thread_to_nodes[thread_id] = set()
        self._thread_to_nodes[thread_id].add(node_id)
        
        return self._thread_to_view_index[thread_id]
    
    def unregister_node(self, node_id: int, thread_id: str) -> bool:
        """
        从线程中移除节点
        
        如果线程变空（且不是 main 线程），会自动删除该线程。
        
        Args:
            node_id: 节点ID
            thread_id: 线程ID
            
        Returns:
            如果线程被删除则返回 True，否则返回 False
        """
        if thread_id in self._thread_to_nodes:
            self._thread_to_nodes[thread_id].discard(node_id)
            
            # 检查线程是否变空（main 线程除外）
            if thread_id != "main" and len(self._thread_to_nodes[thread_id]) == 0:
                self._delete_thread(thread_id)
                return True
        return False
    
    def move_node_to_thread(self, node_id: int, old_thread: str, new_thread: str) -> int:
        """
        将节点从一个线程移动到另一个线程
        
        Args:
            node_id: 节点ID
            old_thread: 原线程ID
            new_thread: 新线程ID
            
        Returns:
            新线程的 view_index
        """
        self.unregister_node(node_id, old_thread)
        return self.register_node(node_id, new_thread)
    
    # ========== 线程重命名 ==========
    
    def rename_thread(self, old_name: str, new_name: str) -> bool:
        """
        重命名线程
        
        规则:
        1. main 线程不能被重命名
        2. 新名称不能与已有线程冲突
        
        Args:
            old_name: 原线程名称
            new_name: 新线程名称
            
        Returns:
            重命名是否成功
        """
        # 检查限制条件
        if old_name == "main":
            print("Cannot rename main thread")
            return False
        if old_name not in self._thread_to_view_index:
            print(f"Thread '{old_name}' does not exist")
            return False
        if new_name in self._thread_to_view_index:
            print(f"Thread '{new_name}' already exists")
            return False
        if not new_name or not new_name.strip():
            print("Thread name cannot be empty")
            return False
        
        # 更新 view_index 映射
        view_index = self._thread_to_view_index.pop(old_name)
        self._thread_to_view_index[new_name] = view_index
        
        # 更新 nodes 映射
        nodes = self._thread_to_nodes.pop(old_name, set())
        self._thread_to_nodes[new_name] = nodes
        
        # 发出信号
        self.threadRenamed.emit(old_name, new_name)
        self.threadsChanged.emit(self.get_all_thread_ids())
        
        print(f"Renamed thread: '{old_name}' -> '{new_name}'")
        return True
    
    # ========== 内部方法 ==========
    
    def _create_thread(self, thread_id: str):
        """
        创建新线程
        
        main 线程的 view_index 固定为 0，其他线程递增分配
        """
        if thread_id in self._thread_to_view_index:
            return  # 线程已存在
        
        if thread_id == "main":
            self._thread_to_view_index[thread_id] = 0
        else:
            # 分配新索引: max + 1
            current_indices = list(self._thread_to_view_index.values())
            next_idx = max(current_indices) + 1 if current_indices else 1
            self._thread_to_view_index[thread_id] = next_idx
        
        self._thread_to_nodes[thread_id] = set()
        self.threadsChanged.emit(self.get_all_thread_ids())
        print(f"Created thread: '{thread_id}' (view_index: {self._thread_to_view_index[thread_id]})")
    
    def _delete_thread(self, thread_id: str):
        """
        删除线程并重新排序其他线程的 view_index
        
        规则:
        1. main 线程不能被删除
        2. 删除后，所有 view_index > deleted_index 的线程索引 -1
        """
        if thread_id == "main":
            print("Cannot delete main thread")
            return
        
        if thread_id not in self._thread_to_view_index:
            return
        
        del_view_id = self._thread_to_view_index.pop(thread_id)
        self._thread_to_nodes.pop(thread_id, None)
        
        # 更新其他线程的 view_index
        for tid in self._thread_to_view_index:
            if self._thread_to_view_index[tid] > del_view_id:
                self._thread_to_view_index[tid] -= 1
        
        # 发出信号
        self.threadDeleted.emit(thread_id)
        self.viewIndicesChanged.emit()
        self.threadsChanged.emit(self.get_all_thread_ids())
        
        print(f"Deleted empty thread: '{thread_id}' (was view_index: {del_view_id})")
    
    # ========== 同步方法（与 GuiExecutionPlan 交互）==========
    
    def sync_from_plan(self, plan: 'GuiExecutionPlan'):
        """
        从 GuiExecutionPlan 同步数据（加载文件时使用）
        
        这会完全重置 ThreadManager 的状态
        """
        self._thread_to_view_index.clear()
        self._thread_to_nodes.clear()
        
        # 从 plan 复制 threadId_map_viewId
        self._thread_to_view_index.update(plan.threadId_map_viewId)
        
        # 从节点列表重建 thread_to_nodes 映射
        for node in plan.nodes:
            tid = node.thread_id
            if tid not in self._thread_to_nodes:
                self._thread_to_nodes[tid] = set()
            self._thread_to_nodes[tid].add(node.node_id)
        
        self.threadsChanged.emit(self.get_all_thread_ids())
        print(f"Synced from plan: {len(self._thread_to_view_index)} threads, {sum(len(nodes) for nodes in self._thread_to_nodes.values())} nodes")
    
    def sync_to_plan(self, plan: 'GuiExecutionPlan'):
        """
        同步数据到 GuiExecutionPlan（保存文件时使用）
        """
        plan.threadId_map_viewId = self._thread_to_view_index.copy()
    
    def clear(self):
        """清空所有数据（切换 pattern 时使用）"""
        self._thread_to_view_index.clear()
        self._thread_to_nodes.clear()
        self.threadsChanged.emit([])
