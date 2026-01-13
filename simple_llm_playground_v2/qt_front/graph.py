from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsLineItem, QGraphicsPathItem, QPushButton, QGraphicsDropShadowEffect, QMenu
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import QPen, QBrush, QColor, QWheelEvent, QPainter, QPainterPath, QFont
import random
import json
from utils import NODE_COLORS, THREAD_COLORS

class NodeItem(QGraphicsItem):
    """
    Custom Node Item with rounded corners, header, and shadow.
    """
    def __init__(self, node_data, x=0, y=0, w=180, h=80, thread_color=None):
        super().__init__()
        self.setPos(x, y)
        self.width = w
        self.height = h
        self.node_data = node_data
        self.thread_color = thread_color  # Color for thread distinction
        
        # Output anchor for drag connections (right side)
        self.output_anchor_rect = QRectF(self.width - 12, self.height/2 - 6, 12, 12)
        
        # Swap buttons (left and right arrows next to ID)
        # These will be positioned dynamically in paint method
        self.left_swap_rect = QRectF(0, 0, 0, 0)  # Will be set in paint
        self.right_swap_rect = QRectF(0, 0, 0, 0)  # Will be set in paint
        self.hover_swap_button = None  # Track which button is hovered: 'left', 'right', 'up', 'down', or None
        
        # Thread swap buttons (up and down arrows for thread position)
        self.up_thread_rect = QRectF(0, 0, 0, 0)  # Will be set in paint
        self.down_thread_rect = QRectF(0, 0, 0, 0)  # Will be set in paint
        
        # Rule 1: Fixed positions. Disable Movable flag always.
        self.is_fixed = True 
        
        flags = QGraphicsItem.ItemIsSelectable
        # if not self.is_fixed: flags |= QGraphicsItem.ItemIsMovable # Disabled
        
        # Enable hover events for swap buttons
        self.setAcceptHoverEvents(True)
            
        self.setFlags(flags)
        
        # Execution status tracking
        self.execution_status = "pending"  # pending/running/completed/failed
        self.STATUS_COLORS = {
            "pending": QColor("#666666"),
            "running": QColor("#FFC107"),
            "completed": QColor("#4CAF50"),
            "failed": QColor("#F44336")
        }
        
        # Cache colors
        self._update_colors()

    def _update_colors(self):
        # Header color priority: thread_color > custom color > node type color
        if self.thread_color:
            self.header_color = self.thread_color
        elif "color" in self.node_data:
            self.header_color = QColor(self.node_data["color"])
        else:
            ntype = self.node_data.get("node_type", "default")
            self.header_color = NODE_COLORS.get(ntype, NODE_COLORS["default"])
            
        self.body_color = QColor("#2d2d2d")
        self.text_color = QColor("#ffffff")
        self.subtext_color = QColor("#b0b0b0")

    def boundingRect(self):
        # Expand bounds to include the up/down buttons
        # Up button: extends above (if index > 0)
        # Down button: extends below (always)
        
        top = -2
        bottom = self.height + 2
        
        thread_view_index = self.node_data.get("thread_view_index", 0)
        if thread_view_index > 0:
            # Include up button area: 20 button + 4 gap
            top = -28
            
        # Include down button area: 20 button + 4 gap
        bottom = self.height + 28
            
        return QRectF(-2, top, self.width + 4, bottom - top)

    def get_output_anchor_center(self) -> QPointF:
        """Get the center of output anchor in scene coordinates"""
        return self.mapToScene(self.output_anchor_rect.center())
    
    def get_input_point(self) -> QPointF:
        """Get the input connection point (left side)"""
        return self.mapToScene(QPointF(0, self.height / 2))

    def paint(self, painter, option, widget):
        # Update color in case data changed
        self._update_colors()
        
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width, self.height, 8, 8)
        
        # Border: black by default, blue when selected
        if self.isSelected():
            painter.setPen(QPen(QColor("#4a90e2"), 3))
        else:
            painter.setPen(QPen(QColor("#111111"), 1))
            
        # Fill Body
        painter.setBrush(self.body_color)
        painter.drawPath(path)
        
        # Header (Top part) - Slanted Design
        # Taller on the right side
        h_left = 24
        h_right = 38
        
        header_path = QPainterPath()
        header_path.moveTo(0, h_left)
        header_path.lineTo(0, 8)
        header_path.arcTo(0, 0, 16, 16, 180, 90) # Top-left corner
        header_path.lineTo(self.width - 8, 0)
        header_path.arcTo(self.width - 16, 0, 16, 16, 90, -90) # Top-right corner
        header_path.lineTo(self.width, h_right)
        header_path.lineTo(0, h_left)
        
        painter.fillPath(header_path, self.header_color)
        
        # Text (Name)
        painter.setPen(self.text_color)
        font = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(font)
        # Position slightly adjusted for slant
        painter.drawText(QRectF(10, 0, self.width - 20, 30), 
                         Qt.AlignLeft | Qt.AlignVCenter, 
                         self.node_data.get("node_name", "Node"))
        
        # Type Label (Body)
        painter.setPen(self.subtext_color)
        font_small = QFont("Segoe UI", 8)
        painter.setFont(font_small)
        type_text = f"Type: {self.node_data.get('node_type', 'unknown')}"
        
        # Start drawing type text below the lowest part of header
        text_y_start = max(h_left, h_right) + 8
        painter.drawText(QRectF(10, text_y_start, self.width - 20, 20),
                         Qt.AlignLeft, type_text)
        
        # Draw ID with swap buttons
        node_id = self.node_data.get('id', '?')
        thread_id = self.node_data.get('thread_id', 'main')
        
        # Calculate button positions
        button_size = 14
        button_y = text_y_start + 15
        
        # Left arrow button (only show if ID > 1)
        if isinstance(node_id, int) and node_id > 1:
            self.left_swap_rect = QRectF(10, button_y, button_size, button_size)
            # Draw button background
            if self.hover_swap_button == 'left':
                painter.setBrush(QColor("#4a90e2"))
            else:
                painter.setBrush(QColor("#3e3e3e"))
            painter.setPen(QPen(QColor("#555555"), 1))
            painter.drawRoundedRect(self.left_swap_rect, 3, 3)
            
            # Draw left arrow
            painter.setPen(QPen(QColor("#ffffff"), 2))
            arrow_center_x = self.left_swap_rect.center().x()
            arrow_center_y = self.left_swap_rect.center().y()
            painter.drawLine(int(arrow_center_x + 2), int(arrow_center_y),
                           int(arrow_center_x - 2), int(arrow_center_y))
            painter.drawLine(int(arrow_center_x - 2), int(arrow_center_y),
                           int(arrow_center_x), int(arrow_center_y - 3))
            painter.drawLine(int(arrow_center_x - 2), int(arrow_center_y),
                           int(arrow_center_x), int(arrow_center_y + 3))
        else:
            self.left_swap_rect = QRectF(0, 0, 0, 0)
        
        # ID text
        id_x_offset = 10 + (button_size + 4 if isinstance(node_id, int) and node_id > 1 else 0)
        id_text = f"ID: {node_id}"
        painter.setPen(self.subtext_color)
        painter.setFont(font_small)
        id_text_rect = QRectF(id_x_offset, button_y, 50, button_size)
        painter.drawText(id_text_rect, Qt.AlignLeft | Qt.AlignVCenter, id_text)
        
        # Right arrow button (always show, will check validity on click)
        right_button_x = id_x_offset + 52
        self.right_swap_rect = QRectF(right_button_x, button_y, button_size, button_size)
        # Draw button background
        if self.hover_swap_button == 'right':
            painter.setBrush(QColor("#4a90e2"))
        else:
            painter.setBrush(QColor("#3e3e3e"))
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawRoundedRect(self.right_swap_rect, 3, 3)
        
        # Draw right arrow
        painter.setPen(QPen(QColor("#ffffff"), 2))
        arrow_center_x = self.right_swap_rect.center().x()
        arrow_center_y = self.right_swap_rect.center().y()
        painter.drawLine(int(arrow_center_x - 2), int(arrow_center_y),
                       int(arrow_center_x + 2), int(arrow_center_y))
        painter.drawLine(int(arrow_center_x + 2), int(arrow_center_y),
                       int(arrow_center_x), int(arrow_center_y - 3))
        painter.drawLine(int(arrow_center_x + 2), int(arrow_center_y),
                       int(arrow_center_x), int(arrow_center_y + 3))
        
        # Thread ID text (after buttons)
        thread_x_offset = right_button_x + button_size + 4
        # Calculate thread button area first to avoid overlap
        thread_button_size = 20  # Increased from 14 for better visibility
        thread_button_x = self.width - 56  # Adjusted position for larger buttons
        # Limit thread ID text to not overlap with buttons
        thread_text_width = thread_button_x - thread_x_offset - 4  # Leave 4px gap before buttons
        painter.setPen(self.subtext_color)
        painter.drawText(QRectF(thread_x_offset, button_y, max(thread_text_width, 50), button_size),
                         Qt.AlignLeft | Qt.AlignVCenter, f"| {thread_id}")
        
        # Draw thread swap buttons
        # Up button: Position ABOVE the node (negative Y)
        # Down button: Position inside the node at the top
        
        # Up button (only show if thread_view_index > 0, meaning not the topmost thread)
        thread_view_index = self.node_data.get("thread_view_index", 0)
        if thread_view_index > 0:
            # Position up button ABOVE the node (outside the node bounds)
            up_button_y = -thread_button_size - 4  # 4px gap above the node
            up_button_x = self.width / 2 - thread_button_size / 2  # Center horizontally
            self.up_thread_rect = QRectF(up_button_x, up_button_y, thread_button_size, thread_button_size)
            # Draw button background with more visible colors
            if self.hover_swap_button == 'up':
                painter.setBrush(QColor("#5a9fd4"))
            else:
                painter.setBrush(QColor("#4a7ba7"))  # More visible blue-gray color
            painter.setPen(QPen(QColor("#6ab7ff"), 2))  # Brighter border
            painter.drawRoundedRect(self.up_thread_rect, 4, 4)
            
            # Draw up arrow - larger and more visible
            painter.setPen(QPen(QColor("#ffffff"), 3))  # Thicker pen
            arrow_center_x = self.up_thread_rect.center().x()
            arrow_center_y = self.up_thread_rect.center().y()
            # Vertical line (longer)
            painter.drawLine(int(arrow_center_x), int(arrow_center_y + 4),
                           int(arrow_center_x), int(arrow_center_y - 4))
            # Arrow head (wider)
            painter.drawLine(int(arrow_center_x), int(arrow_center_y - 4),
                           int(arrow_center_x - 5), int(arrow_center_y + 1))
            painter.drawLine(int(arrow_center_x), int(arrow_center_y - 4),
                           int(arrow_center_x + 5), int(arrow_center_y + 1))
        else:
            self.up_thread_rect = QRectF(0, 0, 0, 0)
        
        # Down button (always show, will check validity on click)
        # Position down button at bottom-center of the node (outside node bounds)
        down_button_y = self.height + 4  # 4px gap below
        down_button_x = self.width / 2 - thread_button_size / 2  # Center horizontally
        self.down_thread_rect = QRectF(down_button_x, down_button_y, thread_button_size, thread_button_size)
        
        # Draw button background with more visible colors
        if self.hover_swap_button == 'down':
            painter.setBrush(QColor("#5a9fd4"))
        else:
            painter.setBrush(QColor("#4a7ba7"))  # More visible blue-gray color
        painter.setPen(QPen(QColor("#6ab7ff"), 2))  # Brighter border
        painter.drawRoundedRect(self.down_thread_rect, 4, 4)
        
        # Draw down arrow - larger and more visible
        painter.setPen(QPen(QColor("#ffffff"), 3))  # Thicker pen
        arrow_center_x = self.down_thread_rect.center().x()
        arrow_center_y = self.down_thread_rect.center().y()
        # Vertical line (longer)
        painter.drawLine(int(arrow_center_x), int(arrow_center_y - 4),
                       int(arrow_center_x), int(arrow_center_y + 4))
        # Arrow head (wider)
        painter.drawLine(int(arrow_center_x), int(arrow_center_y + 4),
                       int(arrow_center_x - 5), int(arrow_center_y - 1))
        painter.drawLine(int(arrow_center_x), int(arrow_center_y + 4),
                       int(arrow_center_x + 5), int(arrow_center_y - 1))
        
        # Draw output anchor (green circle)
        painter.setBrush(QColor("#4CAF50"))
        painter.setPen(QPen(QColor("#2E7D32"), 1))
        painter.drawEllipse(self.output_anchor_rect)
        
        # Draw execution status indicator (top-right corner)
        if self.execution_status != "pending":
            status_color = self.STATUS_COLORS.get(self.execution_status, QColor("#666666"))
            status_size = 12
            status_x = self.width - status_size - 4
            status_y = 4
            painter.setBrush(status_color)
            painter.setPen(QPen(status_color.darker(120), 1))
            painter.drawEllipse(int(status_x), int(status_y), status_size, status_size)
            
            # Draw icon inside status indicator
            painter.setPen(QPen(QColor("#ffffff"), 2))
            center_x = status_x + status_size / 2
            center_y = status_y + status_size / 2
            
            if self.execution_status == "completed":
                # Draw checkmark
                painter.drawLine(int(center_x - 3), int(center_y), int(center_x - 1), int(center_y + 2))
                painter.drawLine(int(center_x - 1), int(center_y + 2), int(center_x + 3), int(center_y - 2))
            elif self.execution_status == "running":
                # Draw dot
                painter.setBrush(QColor("#ffffff"))
                painter.drawEllipse(int(center_x - 2), int(center_y - 2), 4, 4)
            elif self.execution_status == "failed":
                # Draw X
                painter.drawLine(int(center_x - 2), int(center_y - 2), int(center_x + 2), int(center_y + 2))
                painter.drawLine(int(center_x + 2), int(center_y - 2), int(center_x - 2), int(center_y + 2))


    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
    
    def hoverMoveEvent(self, event):
        """Track hover over swap buttons"""
        local_pos = event.pos()
        
        old_hover = self.hover_swap_button
        

        
        if self.left_swap_rect.contains(local_pos):
            self.hover_swap_button = 'left'
        elif self.right_swap_rect.contains(local_pos):
            self.hover_swap_button = 'right'
        elif self.up_thread_rect.contains(local_pos):
            self.hover_swap_button = 'up'
        elif self.down_thread_rect.contains(local_pos):
            self.hover_swap_button = 'down'
        else:
            self.hover_swap_button = None
        
        # Repaint if hover state changed
        if old_hover != self.hover_swap_button:

            self.update()
        
        super().hoverMoveEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Clear hover state when mouse leaves"""
        if self.hover_swap_button is not None:
            self.hover_swap_button = None
            self.update()
        super().hoverLeaveEvent(event)
    
    def set_execution_status(self, status: str):
        """Set execution status and trigger repaint"""
        if status in self.STATUS_COLORS:
            self.execution_status = status
            self.update()  # Trigger repaint


class ConnectionLine(QGraphicsPathItem):
    """
    Connection line between nodes.
    
    Types:
    - thread: Same thread sequential connection (solid line)
    - data_in: Data input connection (dashed line)
    - data_out: Data output to merge node (dashed line)
    """
    def __init__(self, start_item, end_item, connection_type="thread", color=None):
        super().__init__()
        self.start_item = start_item
        self.end_item = end_item
        self.connection_type = connection_type
        self.line_color = color or QColor("#666666")
        
        self._update_path()
        self._update_style()
        self.setZValue(-1)  # Behind nodes
    
    def _update_style(self):
        if self.connection_type == "thread":
            pen = QPen(self.line_color, 2, Qt.SolidLine)
        else:  # data_in or data_out
            pen = QPen(self.line_color, 2, Qt.DashLine)
        pen.setCapStyle(Qt.RoundCap)
        self.setPen(pen)
    
    def _update_path(self):
        path = QPainterPath()
        
        if isinstance(self.start_item, NodeItem):
            start_pos = self.start_item.get_output_anchor_center()
        else:
            start_pos = self.start_item.get_output_point()
            
        if isinstance(self.end_item, NodeItem):
            end_pos = self.end_item.get_input_point()
        else:
            end_pos = self.end_item.get_input_point()
        
        # Bezier curve for smooth connection
        path.moveTo(start_pos)
        ctrl_offset = abs(end_pos.x() - start_pos.x()) / 2
        ctrl1 = QPointF(start_pos.x() + ctrl_offset, start_pos.y())
        ctrl2 = QPointF(end_pos.x() - ctrl_offset, end_pos.y())
        path.cubicTo(ctrl1, ctrl2, end_pos)
        
        self.setPath(path)
    
    def update_position(self):
        self._update_path()


class MergeNodeItem(QGraphicsItem):
    """
    Merge node (+) - Virtual display node showing where child thread data merges to parent.
    This is not a real node, just a visual indicator.
    """
    def __init__(self, x, y, parent_thread_id, child_thread_id, color=None):
        super().__init__()
        self.setPos(x, y)
        self.size = 36
        self.parent_thread_id = parent_thread_id
        self.child_thread_id = child_thread_id
        self.color = color or QColor("#4CAF50")
        self.setZValue(0)
    
    def boundingRect(self):
        return QRectF(-2, -2, self.size + 4, self.size + 4)
    
    def get_input_point(self) -> QPointF:
        """Get the input connection point"""
        return self.mapToScene(QPointF(0, self.size / 2))
    
    def get_output_point(self) -> QPointF:
        """Get the output connection point"""
        return self.mapToScene(QPointF(self.size, self.size / 2))
    
    def paint(self, painter, option, widget):
        # Draw circle background
        painter.setBrush(self.color)
        painter.setPen(QPen(self.color.darker(120), 2))
        painter.drawEllipse(0, 0, self.size, self.size)
        
        # Draw + sign
        painter.setPen(QPen(QColor("#ffffff"), 3))
        center = self.size / 2
        margin = 8
        painter.drawLine(int(center), int(margin), int(center), int(self.size - margin))
        painter.drawLine(int(margin), int(center), int(self.size - margin), int(center))
        
        # Draw label below
        painter.setPen(QColor("#b0b0b0"))
        font = QFont("Segoe UI", 7)
        painter.setFont(font)
        painter.drawText(QRectF(-20, self.size + 2, self.size + 40, 15),
                        Qt.AlignCenter, f"← {self.child_thread_id}")


class NodeGraphScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-2500, -2500, 5000, 5000)
        self.grid_size = 20
        self.grid_color = QColor("#2d2d2d")
        self.connection_lines = []
        self.merge_nodes = []

    def drawBackground(self, painter, rect):
        # Fill background
        painter.fillRect(rect, QColor("#1e1e1e"))
        
        # Draw Grid
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        
        lines = []
        # Vertical lines
        for x in range(left, int(rect.right()), self.grid_size):
            lines.append(QGraphicsLineItem(x, rect.top(), x, rect.bottom()).line())
        # Horizontal lines
        for y in range(top, int(rect.bottom()), self.grid_size):
            lines.append(QGraphicsLineItem(rect.left(), y, rect.right(), y).line())
            
        painter.setPen(QPen(self.grid_color, 1))
        painter.drawLines(lines)

class NodeGraphView(QGraphicsView):
    nodeSelected = pyqtSignal(dict) # Emit node data when selected

    def __init__(self):
        super().__init__()
        self.scene = NodeGraphScene()
        self.setScene(self.scene)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self.next_node_id = 1
        self.node_gap_x = 220
        
        # Thread color management
        self.thread_color_map = {}  # thread_id -> QColor
        
        # Drag connection state
        self.dragging_connection = False
        self.drag_start_item = None
        self.drag_temp_line = None
        
        # Thread View Index Management
        self.thread_view_indices = {} # thread_id -> index (int)
        
        # Test Data - Position at bottom-left area (positive Y goes down in Qt)
        # Use Y=200 as baseline for main thread (appears in lower area of screen)
        self.main_y_baseline = 200
        self.add_node({"node_name": "main", "node_type": "llm-first", "thread_id": "main", "task_prompt": "", "fixed": True, "thread_view_index": 0}, 0, self.main_y_baseline)
        
        # Center view on bottom-left area to show first node at screen's bottom-left
        # Offset the center to the right and down to position first node at bottom-left
        self.center_to_bottom_left()
        
        # Add overlay button
        self.add_btn = QPushButton("+", self)
        self.add_btn.setGeometry(20, 20, 40, 40)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border-radius: 20px;
                font-family: Arial;
                font-weight: bold;
                font-size: 24px;
                border: 1px solid #1e88e5;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                background-color: #42a5f5;
            }
            QPushButton:pressed {
                background-color: #1976d2;
            }
        """)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.add_node_at_center)
        
        # Add shadow to button
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 4)
        self.add_btn.setGraphicsEffect(shadow)
    
    def center_to_bottom_left(self):
        """Center view to show first node at bottom-left of screen"""
        # Get the visible viewport size
        viewport_rect = self.viewport().rect()
        viewport_width = viewport_rect.width()
        viewport_height = viewport_rect.height()
        
        # Calculate offset to position node (at 0, main_y_baseline) at bottom-left of viewport
        # We want the node to appear with some margin from the edges
        margin_x = 150  # Horizontal margin from left edge
        margin_y = 150  # Vertical margin from bottom edge
        
        # Center point calculation: we want the node at (0, main_y_baseline) to appear
        # at (margin_x, viewport_height - margin_y) in viewport coordinates
        # So the center of the view should be at:
        center_x = 0 + (viewport_width / 2 - margin_x)
        center_y = self.main_y_baseline + (viewport_height / 2 - margin_y)
        
        self.centerOn(-center_x + margin_x, center_y - margin_y)

    def get_thread_color(self, thread_id: str) -> QColor:
        """Get or create a color for a thread_id"""
        if thread_id not in self.thread_color_map:
            idx = len(self.thread_color_map)
            color_hex = THREAD_COLORS[idx % len(THREAD_COLORS)]
            self.thread_color_map[thread_id] = QColor(color_hex)
        return self.thread_color_map[thread_id]
    
    def update_connections(self):
        """Rebuild all connection lines based on current nodes"""
        # Clear existing connections
        for line in self.scene.connection_lines:
            self.scene.removeItem(line)
        self.scene.connection_lines.clear()
        
        for merge in self.scene.merge_nodes:
            self.scene.removeItem(merge)
        self.scene.merge_nodes.clear()
        
        # Get all nodes sorted by ID
        nodes = [i for i in self.scene.items() if isinstance(i, NodeItem)]
        nodes.sort(key=lambda n: n.node_data.get("id", 0))
        
        # Build node lookup by id
        node_by_id = {n.node_data.get("id"): n for n in nodes}
        
        # Group nodes by thread_id
        threads = {}
        for node in nodes:
            tid = node.node_data.get("thread_id", "main")
            if tid not in threads:
                threads[tid] = []
            threads[tid].append(node)
        
        # Draw same-thread connections (solid lines)
        for tid, thread_nodes in threads.items():
            thread_nodes.sort(key=lambda n: n.node_data.get("id", 0))
            color = self.get_thread_color(tid)
            
            for i in range(len(thread_nodes) - 1):
                start_node = thread_nodes[i]
                end_node = thread_nodes[i + 1]
                line = ConnectionLine(start_node, end_node, "thread", color)
                self.scene.addItem(line)
                self.scene.connection_lines.append(line)
        
        # Draw data_in connections (dashed lines) and merge nodes for data_out
        for node in nodes:
            # data_in connection
            data_in_thread = node.node_data.get("data_in_thread")
            if data_in_thread and data_in_thread in threads:
                source_nodes = threads[data_in_thread]
                target_id = node.node_data.get("id", 0)
                # Find the last node in source thread that has id < target_id
                valid_sources = [n for n in source_nodes if n.node_data.get("id", 0) < target_id]
                if valid_sources:
                    # Connect from the last valid source node
                    source_node = max(valid_sources, key=lambda n: n.node_data.get("id", 0))
                    line = ConnectionLine(source_node, node, "data_in", 
                                         self.get_thread_color(data_in_thread))
                    self.scene.addItem(line)
                    self.scene.connection_lines.append(line)
            
            # data_out - create merge node on parent thread
            if node.node_data.get("data_out"):
                parent_tid = node.node_data.get("parent_thread_id", "main")
                child_tid = node.node_data.get("thread_id", "main")
                
                if parent_tid and parent_tid != child_tid and parent_tid in threads:
                    # Place merge node at appropriate X position (after this node)
                    merge_x = node.x() + self.node_gap_x / 2
                    # Y position on parent thread (Y=0 for main)
                    parent_y = 0
                    if threads[parent_tid]:
                        parent_y = threads[parent_tid][0].y()
                    
                    merge_node = MergeNodeItem(
                        merge_x, parent_y + 20,
                        parent_tid, child_tid,
                        self.get_thread_color(child_tid)
                    )
                    self.scene.addItem(merge_node)
                    self.scene.merge_nodes.append(merge_node)
                    
                    # Draw line from node to merge node
                    line = ConnectionLine(node, merge_node, "data_out",
                                         self.get_thread_color(child_tid))
                    self.scene.addItem(line)
                    self.scene.connection_lines.append(line)

    def get_all_nodes_data(self):
        nodes = []
        # Sort by x position to maintain some logical order if needed
        items = [i for i in self.scene.items() if isinstance(i, NodeItem)]
        items.sort(key=lambda item: item.x())
        
        for item in items:
            # Update position in data just in case we want to persist it later (custom field)
            item.node_data["_ui_pos"] = [item.x(), item.y()]
            nodes.append(item.node_data)
        return nodes

    def clear_nodes(self):
        self.scene.clear()

    def auto_layout_nodes(self, nodes_data):
        self.clear_nodes()
        self.next_node_id = 1
        
        # ID re-mapping for parent/child consistency
        old_id_map = {}
        
        # Map existing thread indices if present
        for node in nodes_data:
            tid = node.get("thread_id", "main")
            tidx = node.get("thread_view_index")
            if tidx is not None and tid not in self.thread_view_indices:
                self.thread_view_indices[tid] = tidx

        # First pass: Assign new IDs and Map
        for node in nodes_data:
            # Ensure thread_view_index
            tid = node.get("thread_id", "main")
            if tid not in self.thread_view_indices:
                # Assign new index: max + 1
                current_indices = self.thread_view_indices.values()
                next_idx = max(current_indices) + 1 if current_indices else 0
                self.thread_view_indices[tid] = next_idx
            
            node["thread_view_index"] = self.thread_view_indices[tid]

            old_id = node.get("id")
            new_id = self.next_node_id
            
            node["id"] = new_id
            if old_id is not None:
                old_id_map[old_id] = new_id
            
            # Auto-assign color for existing planning nodes if missing
            if node.get("node_type") == "planning" and "color" not in node:
                # Assign a deterministic but unique-looking color based on ID to be stable? 
                # Or just random? User said "different". Random is fine but changes on reload if not saved.
                # Let's use random but it will be saved next time they save.
                node["color"] = QColor.fromHsv(random.randint(0, 359), 200, 200).name()

            self.next_node_id += 1
            
        # Second pass: Update parent pointers if they exist (assuming 'parent_id' key)
        # and Add to Scene
        
        # Reset counter for adding to scene (add_node increments it if we don't provide force_id, 
        # but here we want to trust our pre-calculated IDs or just let add_node handle it if we pass processed data)
        # Actually easier: just call add_node sequentially.
        
        # Wait, add_node logic below handles X based on ID. 
        # So we just need to respect the Y from saved layout if available.
        # But we MUST rewrite IDs in the data to be sequential 1..N based on list order.
        
        # Reset ID again so add_node starts from 1 matching our loop
        self.next_node_id = 1
        
        for node in nodes_data:
            # Fix parent_id if needed
            pid = node.get("parent_id")
            if pid in old_id_map:
                node["parent_id"] = old_id_map[pid]
            
            # Determine Y based on thread_view_index (Top-Down per requirement)
            # "One vertical coordinate can only have one thread"
            # User Feedback: "id越大应该是往上的" (Larger ID should be upwards).
            # In Qt, Up is negative Y relative to baseline.
            # So we SUBTRACT the offset.
            
            tidx = node.get("thread_view_index", 0)
            thread_gap_y = 120 # Vertical spacing between threads
            
            y = self.main_y_baseline - (tidx * thread_gap_y)
            
            # Override with saved _ui_pos ONLY for X (dragged horizontally?) 
            # Or ignore Y completely to enforce strict layout.
            if "_ui_pos" in node:
                # node["_ui_pos"][1] = y # Force Y to match thread
                pass 
            
            
            # X is determined by ID in add_node
            self.add_node(node, 0, y)
        
        # Draw connections after all nodes are placed
        self.update_connections()
    
    def update_node_color(self, node_data):
        """Update the color of a specific node when its thread_id changes"""
        # Find the node item with matching data
        nodes = [i for i in self.scene.items() if isinstance(i, NodeItem)]
        for node in nodes:
            if node.node_data.get("id") == node_data.get("id"):
                # Get new thread color
                thread_id = node_data.get("thread_id", "main")
                new_color = self.get_thread_color(thread_id)
                node.thread_color = new_color
                # Force repaint
                node.update()
                break
        
        # Update all connections since thread relationships may have changed
        self.update_connections()
    
    def update_node_status(self, node_id: int, status: str):
        """
        Update the execution status of a specific node by ID
        
        Args:
            node_id: The ID of the node to update
            status: One of 'pending', 'running', 'completed', 'failed'
        """
        nodes = [i for i in self.scene.items() if isinstance(i, NodeItem)]
        for node in nodes:
            if node.node_data.get("id") == node_id:
                node.set_execution_status(status)
                break

    def add_node(self, node_data, x, y, force_id=None):
        # Enforce ID
        if force_id is not None:
            node_id = force_id
            # Ensure next_node_id is ahead of forced one to avoid collision if mixed usage
            if node_id >= self.next_node_id:
                self.next_node_id = node_id + 1
        else:
            # Check if data already has an ID (e.g. from file load but not forced via arg)
            # But requirements say "If reading, then according to reading order".
            # So we usually just overwrite/assign based on current counter.
            node_id = self.next_node_id
            self.next_node_id += 1
        
        node_data["id"] = node_id
        
        # Ensure thread_id exists
        if "thread_id" not in node_data:
            node_data["thread_id"] = "main"
            
        # Ensure thread_view_index exists
        tid = node_data["thread_id"]

        if "thread_view_index" not in node_data:
            if tid in self.thread_view_indices:
                node_data["thread_view_index"] = self.thread_view_indices[tid]
            else:
                # New thread dynamic assignment
                # Warning: adding a simple node shouldn't usually create a new thread index unless it IS a new thread.
                # If it's a new thread_id not seen before, assign next index.
                current_indices = self.thread_view_indices.values()
                next_idx = max(current_indices) + 1 if current_indices else 0
                self.thread_view_indices[tid] = next_idx
                node_data["thread_view_index"] = next_idx

        else:
             # Sync back to manager if not present
             if tid not in self.thread_view_indices:
                 self.thread_view_indices[tid] = node_data["thread_view_index"]


        # Enforce X Coordinate based on ID
        # ID 1 -> 0
        # ID 2 -> GAP
        # ...
        calculated_x = (node_id - 1) * self.node_gap_x
        
        # Enforce Y Coordinate based on thread_view_index
        thread_gap_y = 120
        tidx = node_data["thread_view_index"]
        # Larger Index = Higher Up = Smaller Y value
        calculated_y = self.main_y_baseline - (tidx * thread_gap_y)
        
        # Ignore passed 'y' argument in favor of strict thread layout?
        # The 'y' arg is often calculated from parent.y() - 120 etc.
        # We should use strict calculation.
        y = calculated_y
        
        # Get thread color
        thread_color = self.get_thread_color(node_data["thread_id"])
        
        item = NodeItem(node_data, calculated_x, y, thread_color=thread_color)
        self.scene.addItem(item)
    
    def wheelEvent(self, event: QWheelEvent):
        # Zoom
        zoomInFactor = 1.1
        zoomOutFactor = 1 / zoomInFactor
        if event.angleDelta().y() > 0:
            zoomFactor = zoomInFactor
        else:
            zoomFactor = zoomOutFactor
        self.scale(zoomFactor, zoomFactor)

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        
        # Check if clicking on swap buttons or output anchor of a NodeItem
        if isinstance(item, NodeItem):
            local_pos = item.mapFromScene(self.mapToScene(event.pos()))
            
            # Check swap buttons first (higher priority than anchor)
            if item.left_swap_rect.contains(local_pos):
                # Swap with left neighbor
                self.swap_nodes(item, -1)
                return
            elif item.right_swap_rect.contains(local_pos):
                # Swap with right neighbor
                self.swap_nodes(item, 1)
                return
            elif item.up_thread_rect.contains(local_pos):
                # Move thread up
                self.swap_threads(item, -1)
                return
            elif item.down_thread_rect.contains(local_pos):
                # Move thread down
                self.swap_threads(item, 1)
                return
            elif item.output_anchor_rect.contains(local_pos):
                # Start connection drag
                self.dragging_connection = True
                self.drag_start_item = item
                self.drag_temp_line = QGraphicsLineItem()
                self.drag_temp_line.setPen(QPen(QColor("#4CAF50"), 2, Qt.DashLine))
                self.drag_temp_line.setZValue(10)
                self.scene.addItem(self.drag_temp_line)
                start_pos = item.get_output_anchor_center()
                self.drag_temp_line.setLine(start_pos.x(), start_pos.y(),
                                           start_pos.x(), start_pos.y())
                return
            else:
                self.nodeSelected.emit(item.node_data)
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.dragging_connection and self.drag_temp_line:
            start_pos = self.drag_start_item.get_output_anchor_center()
            end_pos = self.mapToScene(event.pos())
            self.drag_temp_line.setLine(start_pos.x(), start_pos.y(),
                                       end_pos.x(), end_pos.y())
            return
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if self.dragging_connection:
            # Hide temp line to find actual item underneath
            if self.drag_temp_line:
                self.drag_temp_line.hide()
            
            # Find target node at release position
            scene_pos = self.mapToScene(event.pos())
            items_at_pos = self.scene.items(scene_pos)
            target = None
            for item in items_at_pos:
                if isinstance(item, NodeItem) and item != self.drag_start_item:
                    target = item
                    break
            
            if target:
                # Validate: source.id < target.id
                source_id = self.drag_start_item.node_data.get("id", 0)
                target_id = target.node_data.get("id", 0)
                
                if source_id < target_id:
                    # Create data_in connection
                    source_thread = self.drag_start_item.node_data.get("thread_id", "main")
                    target.node_data["data_in_thread"] = source_thread
                    target.node_data["data_in_slice"] = (-1, None)  # Default: last message
                    print(f"Created connection: {source_thread} -> Node {target_id}")
                    self.update_connections()
                else:
                    print(f"Invalid connection: source ID ({source_id}) must be < target ID ({target_id})")
            
            # Clean up drag state
            if self.drag_temp_line:
                self.scene.removeItem(self.drag_temp_line)
                self.drag_temp_line = None
            self.dragging_connection = False
            self.drag_start_item = None
            return
        
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, NodeItem):
            menu = QMenu(self)
            add_node_action = menu.addAction("Add Node")
            add_branch_action = menu.addAction("Create Branch Point")
            menu.addSeparator()
            delete_thread_action = menu.addAction("Delete Thread")
            delete_action = menu.addAction("Delete Node")
            
            action = menu.exec_(self.mapToGlobal(event.pos()))
            
            if action == add_node_action:
                self.add_new_node_from(item)
            elif action == add_branch_action:
                self.add_branch_from(item)
            elif action == delete_action:
                self.delete_node(item)
            elif action == delete_thread_action:
                self.delete_thread(item)

    def add_new_node_from(self, parent_item):
        # Extension: Same Y level, same thread
        new_y = parent_item.y()
        parent_thread = parent_item.node_data.get("thread_id", "main")
        
        new_data = {
            "node_name": "New Node", 
            "node_type": "llm-first", 
            "thread_id": parent_thread,
            "task_prompt": "",
            "parent_id": parent_item.node_data.get("id")
        }
        self.add_node(new_data, 0, new_y)
        self.update_connections()

    def add_branch_from(self, parent_item):
        # Branch: Position UPWARDS (negative Y in Qt)
        new_y = parent_item.y() - 120
        parent_thread = parent_item.node_data.get("thread_id", "main")
        
        # Create new thread id for branch
        new_thread_id = f"branch_{self.next_node_id}"

        # Use next available index
        current_indices = self.thread_view_indices.values()
        next_idx = max(current_indices) + 1 if current_indices else 1 # 0 is main
        
        # Register new thread
        self.thread_view_indices[new_thread_id] = next_idx
        
        new_data = {
            "node_name": "Branch", 
            "node_type": "llm-first",
            "thread_id": new_thread_id,
            "parent_thread_id": parent_thread,
            "task_prompt": "",
            "parent_id": parent_item.node_data.get("id"),
            "thread_view_index": next_idx
        }

        # Y will be calculated by add_node
        self.add_node(new_data, 0, 0)
        self.update_connections()

    def delete_node(self, item):
        deleted_id = item.node_data.get("id", 0)
        self.scene.removeItem(item)
        
        # Renumber all nodes with ID > deleted_id
        nodes = [i for i in self.scene.items() if isinstance(i, NodeItem)]
        for node in nodes:
            node_id = node.node_data.get("id", 0)
            if node_id > deleted_id:
                new_id = node_id - 1
                node.node_data["id"] = new_id
                # Recalculate X position based on new ID
                node.setPos((new_id - 1) * self.node_gap_x, node.y())
        
        # Decrement next_node_id counter
        self.next_node_id = max(1, self.next_node_id - 1)
        
        self.update_connections()
    
    def delete_thread(self, item):
        """
        Delete the entire thread that this node belongs to.
        Apply specific shift logic: 'others smaller than his thread coordinate id + 1'
        """
        thread_id = item.node_data.get("thread_id", "main")
        if thread_id == "main":
            print("Cannot delete main thread yet")
            return
            
        deleted_idx = self.thread_view_indices.get(thread_id)
        if deleted_idx is None:
            return
            
        # 1. Remove all nodes of this thread
        nodes_to_remove = []
        for i in self.scene.items():
            if isinstance(i, NodeItem) and i.node_data.get("thread_id") == thread_id:
                nodes_to_remove.append(i)
        
        for node in nodes_to_remove:
            self.scene.removeItem(node)
            
        # 2. Update Indices
        # Rule: "Delete that thread's all IDs, others smaller than his thread coordinate id + 1"
        del self.thread_view_indices[thread_id]
        
        for tid, idx in self.thread_view_indices.items():
            if idx < deleted_idx:
                self.thread_view_indices[tid] = idx + 1
        
        # 3. Update all remaining nodes positions
        remaining_nodes = [i for i in self.scene.items() if isinstance(i, NodeItem)]
        for node in remaining_nodes:
            tid = node.node_data.get("thread_id", "main")
            if tid in self.thread_view_indices:
                new_idx = self.thread_view_indices[tid]
                node.node_data["thread_view_index"] = new_idx
                # Recalculate Y (Larger Index = Upwards = Negative Offset)
                node.setPos(node.x(), self.main_y_baseline - (new_idx * 120))
        
        self.update_connections()

    def swap_nodes(self, item, direction):
        """
        Swap node with its neighbor.
        
        Args:
            item: The NodeItem to swap
            direction: -1 for left swap, 1 for right swap
        """
        current_id = item.node_data.get("id", 0)
        target_id = current_id + direction
        
        # Protect ID=1 node - it cannot be swapped
        if current_id == 1:
            print("Cannot swap: Node ID 1 (main) is protected and cannot be swapped")
            return
        
        # Cannot swap with ID=1 node
        if target_id == 1:
            print("Cannot swap: Cannot swap with Node ID 1 (main) - it is protected")
            return
        
        # Validate target ID
        if target_id < 1:
            print(f"Cannot swap: target ID {target_id} is invalid (must be >= 1)")
            return
        
        # Get all nodes
        nodes = [i for i in self.scene.items() if isinstance(i, NodeItem)]
        
        # Find target node
        target_node = None
        for node in nodes:
            if node.node_data.get("id") == target_id:
                target_node = node
                break
        
        if not target_node:
            print(f"Cannot swap: no node found with ID {target_id}")
            return
        
        # Swap IDs
        item.node_data["id"] = target_id
        target_node.node_data["id"] = current_id
        
        # Recalculate positions based on new IDs
        item.setPos((target_id - 1) * self.node_gap_x, item.y())
        target_node.setPos((current_id - 1) * self.node_gap_x, target_node.y())
        
        # Force repaint
        item.update()
        target_node.update()
        
        # Update all connections
        self.update_connections()
        
        print(f"Swapped nodes: {current_id} ↔ {target_id}")

    def swap_threads(self, item, direction):
        """
        Swap thread position with adjacent thread.
        
        Args:
            item: The NodeItem whose thread should be moved
            direction: -1 for up (move thread up), 1 for down (move thread down)
        """
        current_thread_id = item.node_data.get("thread_id", "main")
        current_thread_index = item.node_data.get("thread_view_index", 0)
        target_thread_index = current_thread_index + direction
        
        # Validate target index
        if target_thread_index < 0:
            print(f"Cannot move thread: target index {target_thread_index} is invalid (must be >= 0)")
            return
        
        # Find target thread (thread with target_thread_index)
        target_thread_id = None
        for tid, idx in self.thread_view_indices.items():
            if idx == target_thread_index:
                target_thread_id = tid
                break
        
        if not target_thread_id:
            print(f"Cannot move thread: no thread found with index {target_thread_index}")
            return
        
        # Swap thread_view_indices
        self.thread_view_indices[current_thread_id] = target_thread_index
        self.thread_view_indices[target_thread_id] = current_thread_index
        
        # Get all nodes
        nodes = [i for i in self.scene.items() if isinstance(i, NodeItem)]
        
        # Update all nodes in both threads
        thread_gap_y = 120
        for node in nodes:
            node_thread_id = node.node_data.get("thread_id", "main")
            if node_thread_id == current_thread_id:
                # Update thread_view_index for all nodes in current thread
                node.node_data["thread_view_index"] = target_thread_index
                # Recalculate Y position
                new_y = self.main_y_baseline - (target_thread_index * thread_gap_y)
                node.setPos(node.x(), new_y)

                node.update()
            elif node_thread_id == target_thread_id:
                # Update thread_view_index for all nodes in target thread
                node.node_data["thread_view_index"] = current_thread_index
                # Recalculate Y position
                new_y = self.main_y_baseline - (current_thread_index * thread_gap_y)
                node.setPos(node.x(), new_y)

                node.update()
        
        # Update all connections
        self.update_connections()
        
        print(f"Swapped threads: {current_thread_id} (index {current_thread_index}) ↔ {target_thread_id} (index {target_thread_index})")

    def add_node_at_center(self):
        # Always add to main axis at main_y_baseline
        new_data = {
            "node_name": "New Node", 
            "node_type": "llm-first", 
            "task_prompt": ""
        }
        self.add_node(new_data, 0, self.main_y_baseline)


