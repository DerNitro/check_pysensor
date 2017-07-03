#!/bin/env python3

"""

"""
import argparse
import os

__author__ = "Sergey V. Utkin"
__copyright__ = "Copyright 2017, Sergey V. Utkin"
__license__ = "GPLv3"
__version__ = "0.1"
__email__ = "utkins01@gmail.com"

parser = argparse.ArgumentParser(description='Плагин мониторинга тепмературы, для Nagios')
parser.add_argument('--version', action='version',
                    version='%(prog)s {version}'.format(version=__version__))

parser.add_argument('--module', help='Проверяемый модуль')
parser.add_argument('--sub', help='Проверяемый сенсор')
parser.add_argument('--warning', help='Высокая температура')
parser.add_argument('--critical', help='Критическая температура')
parser.add_argument('--list', '-l', action='store_true', help='Список доступных сенсоров')
args = parser.parse_args()

HWMON_PATH = '/sys/class/hwmon'
RETURN_CODE = {"OK": 0,
               "Warning": 1,
               "Critical": 2,
               "Unknown": 3}


def read_sensor(path_to_sensor):
    if os.path.isfile(path_to_sensor):
        try:
            with open(path_to_sensor, 'r') as r_file:
                return r_file.readline().rstrip()
        except IOError:
            return None
    else:
        return None


class Module:
    def __init__(self, module_name, module_path):
        self.name = module_name
        self.path = module_path
        self.sensor = []

    def discovery(self):
        s_list = set()
        for f_list in os.listdir(self.path):
            if os.path.isfile(os.path.join(self.path, f_list)) and str(f_list.split('_')[0]).find('temp') >= 0:
                s_list.add(f_list.split('_')[0])
        for sens in sorted(s_list):
            self.sensor.append(Sensor(sens,
                                      read_sensor(os.path.join(self.path, sens + '_input')),
                                      sensor_name=read_sensor(os.path.join(self.path, sens + '_label')),
                                      t_max=read_sensor(os.path.join(self.path, sens + '_max')),
                                      t_crit=read_sensor(os.path.join(self.path, sens + '_crit'))
                                      ))

    def show(self):
        print(self.name)
        for sens in self.sensor:
            print("  {0:<15}\t{1}C (WARN - {2}; CRIT - {3})".format(sens.name, sens.current, sens.t_max, sens.t_crit))

    def __repr__(self):
        return "{0}".format(self.__dict__)


class Sensor:
    def __init__(self, raw_name, current, sensor_name='', t_max='', t_crit=''):
        self.raw_name = raw_name
        if sensor_name is None:
            self.name = self.raw_name
        else:
            self.name = sensor_name
        self.current = float(current) / 1000
        if t_max is not None:
            self.t_max = float(t_max) / 1000
        else:
            self.t_max = float(80)
        if t_crit is not None:
            self.t_crit = float(t_crit) / 1000
        else:
            self.t_crit = float(100)

    def check(self):
        if args.warning:
            self.t_max = float(args.warning)
        if args.critical:
            self.t_crit = float(args.critical)

        if self.current < self.t_max:
            return "OK"

        if self.t_max < self.current < self.t_crit:
            return "Warning"

        if self.current > self.t_crit:
            return "Critical"

    def __repr__(self):
        return "{0}".format(self.__dict__)


modules = []
for hwmon in os.listdir(HWMON_PATH):
    path = os.path.join(HWMON_PATH, hwmon)
    with open(os.path.join(path, 'name'), 'r') as f:
        name = f.readline().rstrip()
    modules.append(Module(module_name=name, module_path=path))

for m in modules:
    m.discovery()

if args.list:
    for m in modules:
        print("Module: {0}".format(m.name))
        for s in m.sensor:
            print("\tSub: {0}".format(s.raw_name))
    exit(RETURN_CODE["OK"])

c_module = None
c_sensor = None
if args.module and args.sub:
    for m in modules:
        if m.name == args.module:
            c_module = m
    if c_module:
        for s in c_module.sensor:
            if s.raw_name == args.sub:
                c_sensor = s
    else:
        print('Нет указаного модуля!!')
        exit(RETURN_CODE["Critical"])

    if c_sensor:
        R = c_sensor.check()
        print("{1} {0} {2}°C = {2}°C;{3};{4}".format(c_sensor.name,
                                                     R,
                                                     c_sensor.current,
                                                     c_sensor.t_max,
                                                     c_sensor.t_crit))
        exit(RETURN_CODE[R])

else:
    for m in modules:
        m.show()

exit(RETURN_CODE["OK"])
