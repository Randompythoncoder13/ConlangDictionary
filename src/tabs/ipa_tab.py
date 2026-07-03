from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea

from src.custom_widgets import IPATable
from src.IPA_tables import PC_TABLE_DATA, NPC_TABLE_DATA, V_TABLE_DATA, OA_TABLE_DATA


class IPATab(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app

        self.pc_table = IPATable(PC_TABLE_DATA, 9, 12, self)
        self.npc_table = IPATable(NPC_TABLE_DATA, 6, 3, self, 1)
        self.v_table = IPATable(V_TABLE_DATA, 8, 6, self)
        self.oa_table = IPATable(OA_TABLE_DATA, 11, 2, self, 1)

        self.pc_table.setFixedHeight(350)
        self.npc_table.setFixedHeight(230)
        self.v_table.setFixedHeight(310)
        self.oa_table.setFixedHeight(430)

        container_widget = QWidget()
        container_layout = QVBoxLayout(container_widget)
        container_layout.addWidget(self.pc_table)
        container_layout.addWidget(self.npc_table)
        container_layout.addWidget(self.v_table)
        container_layout.addWidget(self.oa_table)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(container_widget)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll_area)
