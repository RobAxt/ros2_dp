#!/usr/bin/env python3

import sys
import rclpy
from rclpy.node import Node
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QSlider, QPushButton, QHBoxLayout, QLineEdit
from PyQt5.QtCore import Qt
from std_msgs.msg import Float64MultiArray
import subprocess
import signal


LIMIT_MIN = 0.0
LIMIT_MAX = 1000.0
MAX_SLIDER_VALUE = 1000


class GainControllerGUI(Node):
    node_name = '/position_controller'  
    param_names = ['gains.joint1.p', 'gains.joint1.d', 'gains.joint1.i',
        'gains.joint2.p', 'gains.joint2.d', 'gains.joint2.i',
         'gains.joint3.p', 'gains.joint3.d', 'gains.joint3.i']

    def __init__(self):
        super().__init__('gain_controller_gui')
        #self.publisher_ = self.create_publisher(Float64MultiArray, '/position_controller/params', 10)
        self.get_initial_gains()
        self.init_gui()

    def get_initial_gains(self):
        self.initial_gains = {}
        try:            
            for param_key in self.param_names:
                value = get_param_from_cli(self.node_name, param_key)
                self.initial_gains[param_key] = value
                print(f'{param_key}: {value}')
        except Exception as e:
            self.get_logger().warn(f'Error al obtener ganancias iniciales: {e}')
            self.initial_gains[param_key] = 0.0

    def send_gains(self):
        gains = [float(self.text_inputs[param_key].text()) for param_key in self.param_names]
        try:
            for param_key in self.param_names:
                set_param_from_cli(self.node_name, param_key,gains[self.param_names.index(param_key)])
        except Exception as e:
            self.get_logger().warn(f'Error al setear ganancia {param_key}: {e}')

    def init_gui(self):
        self.app = QApplication(sys.argv)
        self.window = QWidget()
        self.window.setWindowTitle('Ganancias del Control')

        layout = QVBoxLayout()

        self.sliders = {}
        self.text_inputs = {}

        for param_key in self.param_names:
            gain_layout = QHBoxLayout()

            label = QLabel(param_key)
            gain_layout.addWidget(label)

            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(MAX_SLIDER_VALUE)
            slider.setValue(int(self.initial_gains[param_key]*MAX_SLIDER_VALUE/LIMIT_MAX))
            gain_layout.addWidget(slider)

            input_box = QLineEdit(f'{self.initial_gains[param_key]:.1f}')
            input_box.setFixedWidth(60)
            gain_layout.addWidget(input_box)

            self.sliders[param_key] = slider
            self.text_inputs[param_key] = input_box

            # Set initial values from controller
            #if key in self.initial_gains:
            #    value = self.initial_gains[key]
            #    input_box.setText(f'{value:.2f}')
            #    slider.setValue(self.gain_to_slider(value))

            slider.valueChanged.connect(lambda val, k=param_key: self.update_input_from_slider(k))
            input_box.editingFinished.connect(lambda k=param_key: self.update_slider_from_input(k))

            layout.addLayout(gain_layout)

        send_button = QPushButton('Enviar ganancias')
        send_button.clicked.connect(self.send_gains)
        layout.addWidget(send_button)

        self.window.setLayout(layout)
        self.window.show()

        # Permite cerrar con Ctrl+C
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        self.app.exec_()

    def update_input_from_slider(self, key):
        slider = self.sliders[key]
        value = self.slider_to_gain(slider.value())
        self.text_inputs[key].setText(f'{value:.1f}')

    def update_slider_from_input(self, key):
        try:
            text = self.text_inputs[key].text()
            value = float(text)
            value = max(min(value, LIMIT_MAX), LIMIT_MIN)
            slider_val = self.gain_to_slider(value)
            self.sliders[key].setValue(slider_val)
        except ValueError:
            pass

    def slider_to_gain(self, slider_value):
        return LIMIT_MIN + (LIMIT_MAX - LIMIT_MIN) * slider_value / MAX_SLIDER_VALUE

    def gain_to_slider(self, gain):
        return int(MAX_SLIDER_VALUE * (gain - LIMIT_MIN) / (LIMIT_MAX - LIMIT_MIN))


def set_param_from_cli(node_name, param_name, param_value):
    try:
        result = subprocess.run(
            ['ros2', 'param', 'set', node_name, param_name, str(param_value)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"{param_name} fijado a {param_value}")
        else:
            print(f'Error: {result.stderr}')
    except Exception as e:
        print(f'Excepción al obtener parámetro: {e}')
    return None

def get_param_from_cli(node_name, param_name):
    try:
        result = subprocess.run(
            ['ros2', 'param', 'get', node_name, param_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Busca la línea con "value:"
            for line in result.stdout.splitlines():
                if 'value' in line:
                    value_str = line.split(':')[-1].strip()
                    try:
                        return float(value_str)
                    except ValueError:
                        return value_str  # Por si es string

        else:
            print(f'Error: {result.stderr}')
    except Exception as e:
        print(f'Excepción al obtener parámetro: {e}')
    return None

def main():
    rclpy.init()

    controller = GainControllerGUI()
    controller.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
