"""
占位符管理面板模块

提供占位符的显示、编辑和替换功能。
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QScrollArea, QFrame,
    QGridLayout, QGroupBox
)
from PyQt5.QtCore import pyqtSignal, Qt
from typing import Dict
import re


class PlaceholderPanel(QWidget):
    """
    占位符管理面板
    
    功能:
    - 显示当前 pattern 的占位符列表
    - 提供值编辑输入框
    - "替换" 按钮触发替换逻辑
    - "自动检测" 按钮扫描 JSON 提取占位符
    
    信号:
    - replaceRequested: 当用户点击替换按钮时发射
    """
    
    replaceRequested = pyqtSignal()  # 请求执行替换
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._placeholder_inputs: Dict[str, QLineEdit] = {}  # placeholder_key -> input widget
        self._setup_ui()
    
    def _setup_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 标题
        title_layout = QHBoxLayout()
        title_label = QLabel("📝 占位符 (Placeholders)")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # 占位符容器
        self._placeholder_container = QWidget()
        self._placeholder_layout = QGridLayout(self._placeholder_container)
        self._placeholder_layout.setContentsMargins(0, 0, 0, 0)
        self._placeholder_layout.setSpacing(5)
        
        # 将容器直接加入布局，不使用 ScrollArea 以自动适应高度
        layout.addWidget(self._placeholder_container)
        
        # 提示标签 (初始显示)
        self._empty_label = QLabel("加载文件后将显示占位符")
        self._empty_label.setStyleSheet("color: #888; font-style: italic;")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._placeholder_layout.addWidget(self._empty_label, 0, 0, 1, 2)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self._replace_btn = QPushButton("🔄 替换并重新加载")
        self._replace_btn.setToolTip("用填写的值替换占位符并重新加载文件")
        self._replace_btn.setStyleSheet("""
            QPushButton {
                background-color: #1565c0;
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
        """)
        self._replace_btn.clicked.connect(self._on_replace_clicked)
        btn_layout.addWidget(self._replace_btn)
        
        layout.addLayout(btn_layout)
        # 添加底部弹簧，确保内容靠上
        layout.addStretch()
    
    def load_placeholders(self, placeholders: dict):
        """
        加载并显示占位符
        
        Args:
            placeholders: 占位符字典，格式如 {"{start_date}": PlaceholderDefinition(...)}
                          或 {"{start_date}": {"description": "...", "value": "..."}}
        """
        # 清空现有内容
        self._clear_placeholders()
        self._placeholder_inputs.clear()
        
        if not placeholders:
            self._empty_label.show()
            return
        
        self._empty_label.hide()
        
        row = 0
        for key, definition in placeholders.items():
            # 支持 PlaceholderDefinition 对象或普通 dict
            if hasattr(definition, 'description'):
                desc = definition.description
                value = definition.value or definition.default
            else:
                desc = definition.get('description', '')
                value = definition.get('value') or definition.get('default', '')
            
            # 占位符名称标签 (Label)
            label_text = key
            if desc:
                label_text += f" ({desc})"
            
            name_label = QLabel(label_text + ":")
            name_label.setStyleSheet("font-weight: bold;")
            name_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._placeholder_layout.addWidget(name_label, row, 0)
            
            # 输入框 (Value)
            input_widget = QLineEdit()
            input_widget.setText(value)
            input_widget.setPlaceholderText(f"输入 {key} 的值")
            self._placeholder_layout.addWidget(input_widget, row, 1)
            
            self._placeholder_inputs[key] = input_widget
            row += 1
    
    def get_replacements(self) -> Dict[str, str]:
        """
        获取占位符替换映射
        
        Returns:
            {"{placeholder}": "value"} 格式的字典
        """
        result = {}
        for key, input_widget in self._placeholder_inputs.items():
            value = input_widget.text().strip()
            if value:  # 只返回有值的占位符
                result[key] = value
        return result
    
    def auto_detect_from_json(self, json_str: str) -> Dict[str, dict]:
        """
        从 JSON 字符串中自动检测占位符
        
        Args:
            json_str: JSON 字符串
            
        Returns:
            检测到的占位符字典 {"{placeholder}": {"description": "", "value": ""}}
        """
        # 匹配 {xxx} 格式，但排除 JSON 语法中的 { 和 }
        # 简单策略：匹配 "{字母或下划线开头的标识符}"
        pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        matches = re.findall(pattern, json_str)
        
        # 去重并构建结果
        detected = {}
        for match in set(matches):
            key = f"{{{match}}}"
            detected[key] = {
                "description": "",
                "default": "",
                "value": ""
            }
        
        return detected
    
    def _clear_placeholders(self):
        """清空占位符容器"""
        # 移除所有子组件 (除了 empty_label)
        while self._placeholder_layout.count() > 1:
            item = self._placeholder_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        
        # 确保 empty_label 在第一个位置
        if self._placeholder_layout.count() == 0:
            self._placeholder_layout.addWidget(self._empty_label, 0, 0, 1, 2)
    
    
    def _on_replace_clicked(self):
        """替换按钮点击处理"""
        self.replaceRequested.emit()


if __name__ == "__main__":
    # 简单测试
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    panel = PlaceholderPanel()
    panel.load_placeholders({
        "{start_date}": {"description": "开始日期", "value": "2026-01-10"},
        "{end_date}": {"description": "结束日期", "value": "2026-01-17"},
    })
    panel.show()
    
    sys.exit(app.exec_())
