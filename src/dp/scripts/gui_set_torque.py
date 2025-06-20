#!/usr/bin/env python3

import sys
import rclpy
from rclpy.node import Node
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QSlider, QPushButton, QHBoxLayout, QLineEdit
from PyQt5.QtCore import Qt
from std_msgs.msg import Float64MultiArray

JOINT_NAMES = ['joint1', 'joint2', 'joint3']
TORQUE_MIN = -20.0  # Nm
TORQUE_MAX = 20.0   # Nm

class JointTorqueGUI(Node):
    def __init__(self):
        super().__init__('joint_torque_gui')
        self.publisher_ = self.create_publisher(Float64MultiArray, '/effort_controller/commands', 10)
        self.init_gui()

    def init_gui(self):
        self.app = QApplication(sys.argv)
        self.window = QWidget()
        self.window.setWindowTitle('Torque en Ejes')

        layout = QVBoxLayout()

        self.sliders = {}
        self.text_inputs = {}

        for joint in JOINT_NAMES:
            joint_layout = QHBoxLayout()

            label = QLabel(f'{joint} [Nm]')
            joint_layout.addWidget(label)

            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(1000)
            slider.setValue(500)  # 0 Nm
            joint_layout.addWidget(slider)

            input_box = QLineEdit('0.00')
            input_box.setFixedWidth(60)
            joint_layout.addWidget(input_box)

            self.sliders[joint] = slider
            self.text_inputs[joint] = input_box

            slider.valueChanged.connect(lambda val, j=joint: self.update_input_from_slider(j))
            input_box.editingFinished.connect(lambda j=joint: self.update_slider_from_input(j))

            layout.addLayout(joint_layout)

        send_button = QPushButton('Aplicar torque')
        send_button.clicked.connect(self.send_torque_command)
        layout.addWidget(send_button)

        release_button = QPushButton('Liberar torque (cero)')
        release_button.clicked.connect(self.release_torque)
        layout.addWidget(release_button)

        self.window.setLayout(layout)
        self.window.show()
        self.app.exec_()

    def update_input_from_slider(self, joint):
        slider = self.sliders[joint]
        value = self.slider_to_torque(slider.value())
        self.text_inputs[joint].setText(f'{value:.2f}')

    def update_slider_from_input(self, joint):
        try:
            text = self.text_inputs[joint].text()
            value = float(text)
            value = max(min(value, TORQUE_MAX), TORQUE_MIN)
            slider_val = self.torque_to_slider(value)
            self.sliders[joint].setValue(slider_val)
        except ValueError:
            pass

    def slider_to_torque(self, slider_value):
        return TORQUE_MIN + (TORQUE_MAX - TORQUE_MIN) * slider_value / 1000.0

    def torque_to_slider(self, torque):
        return int(1000.0 * (torque - TORQUE_MIN) / (TORQUE_MAX - TORQUE_MIN))

    def send_torque_command(self):
        msg = Float64MultiArray()
        msg.data = [self.slider_to_torque(self.sliders[j].value()) for j in JOINT_NAMES]
        self.publisher_.publish(msg)

    def release_torque(self):
        msg = Float64MultiArray()
        msg.data = [0.0 for _ in JOINT_NAMES]
        self.publisher_.publish(msg)

def main():
    rclpy.init()
    gui = JointTorqueGUI()
    gui.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

