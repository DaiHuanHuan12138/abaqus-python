import odbAccess
from abaqusConstants import *
import json
import time
import os
import sys

#==============================================================================#

class ZdfElement:
    def __init__(self, odb):
        self.odb = odb

    @classmethod
    def _node_order_transform(cls, aba_connect, element_type):
        node_order_map = {
            "faceq6": [0, 1, 2, 4, 5, 3],
            "tetra": [1, 0, 2, 3],
            "tetra10": [1, 0, 2, 3, 6, 5, 4, 8, 7, 9],
            "wedge15": [0, 1, 2, 3, 4, 5, 12, 13, 14, 7, 8, 6, 10, 11, 9],
            "pyram13": [0, 1, 2, 3, 4, 9, 10, 11, 12, 5, 6, 7, 8]
        }

        if element_type not in node_order_map:
            return aba_connect

        zdf_connect = []
        for i in node_order_map[element_type]:
            zdf_connect.append(aba_connect[i])
        return zdf_connect

    @classmethod
    def _abaqus_type_2_zdf_type_beam(cls, aba_type):
        if aba_type[1] == 2:
            return "beam2", 6
        elif aba_type[1] == 3:
            return "beam3", 7
        return "unknown", -1

    @classmethod
    def _abaqus_type_2_zdf_type_continuum(cls, aba_type):
        dims, node_num, zdf_type_id = -1, -1, -1
        zdf_type_str = ""
        # TODO: 目前只支持Solid类型中的1、2、3维单元
        # abaqus element的命名规则参照
        # 1. https://classes.engineering.wustl.edu/2009/spring/mase5513/abaqus/docs/v6.6/books/gss/default.htm?startat=ch03s01.html
        # 2. http://130.149.89.49:2080/v2016/books/usb/default.htm?startat=pt06ch29s03ael14.html
        if aba_type[:3] == "C1D": # Continuum element
            dims = 1
        elif aba_type[:3] == "C2D":
            dims = 2
        elif aba_type[:3] == "C3D":
            dims = 3


        # 决定node_num
        node_num_str = ""
        for c in aba_type[3:]:
            if c.isdigit():
                node_num_str += c
            else:
                break
        node_num = int(node_num_str)

        # 决定 zdf_type_id and zdf_type_str
        id_and_str = {
            1: {
                2: ("edge2", 6),
                3: ("edge3", 7),
            },
            2: {
                3: ("faceq3", 20),
                6: ("faceq6", 21),
                4: ("faceq4", 22),
                8: ("faceq8", 23),
            },
            3: {
                4: ("tetra4", 27),
                10: ("tetra10", 28),

                8: ("hexa8", 29),
                20: ("hexa20", 30),
                27: ("hexa27", 31),

                5: ("pyramid5", 32),
                13: ("pyramid13", 33),
                14: ("pyramid14", 34),

                6: ("wedge6", 35),
                7: ("wedge15", 36),
                18: ("wedge18", 37)
            }
        }

        return id_and_str[dims][node_num]

    def _abaqus_type_2_zdf_type(self, aba_type):
        if aba_type[0] == "B":
            return self._abaqus_type_2_zdf_type_beam(aba_type)
        elif aba_type[0] == "C":
            return self._abaqus_type_2_zdf_type_continuum(aba_type)
        return "unknown", -1


    def get_data(self):
        elements = []
        for part_name, part in self.odb.rootAssembly.instances.items():
            elements = part.elements
            break  #TODO：考虑多个part的情况，只取第一个part的element
        type2 = {}
        for element in elements:
            zdf_type, type_id = self._abaqus_type_2_zdf_type(element.type)
            if zdf_type not in type2:
                type2[zdf_type] = {
                    "type id": type_id,
                    "id" : {
                        "__isRecord__": True,
                        "__dims__": [],
                        "__data__": []
                    },
                    "value": {
                        "__isRecord__": True,
                        "__dims__": [],
                        "__data__": []
                    }
                }
            type2[zdf_type]["id"]["__data__"].append(element.label)
            type2[zdf_type]["value"]["__data__"].append(self._node_order_transform(list(element.connectivity), zdf_type))

        for key in type2:
            type2[key]["id"]["__dims__"] = [len(type2[key]["id"]["__data__"])]
            type2[key]["value"]["__dims__"] = [len(type2[key]["value"]["__data__"]),
                                               len(type2[key]["value"]["__data__"][0])]

            if type2[key]["id"]["__data__"][0] is None:
                # 处理id为None的情况
                type2[key]["id"]["__data__"] = list(range(1, len(type2[key]["id"]["__data__"]) + 1))

        return type2

class ZdfModelMesh:
    def __init__(self, odb) -> None:
        self.odb = odb

        # 获取所有节点的id和坐标
        nodes = []
        for part_name, part in self.odb.rootAssembly.instances.items():
            nodes = part.nodes
            break #TODO：考虑多个part的情况，只取第一个part的node
        self.node_ids = []
        self.coordinates = []
        for node in nodes:
            self.node_ids.append(node.label)
            self.coordinates.append(node.coordinates.tolist())

        self.elements = ZdfElement(self.odb)


    def get_data(self):
        result = {
            "nodes" : {
                "id": {
                    "__isRecord__": True,
                    "__dims__": [len(self.node_ids)],
                    "__data__": self.node_ids if self.node_ids[0] is not None else list(range(1, len(self.node_ids) + 1))
                },
                "value": {
                    "__isRecord__": True,
                    "__dims__": [len(self.node_ids), len(self.coordinates[0])],
                    "__data__": self.coordinates
                }
            },
            "elements" : self.elements.get_data()
        }

        return result

class ZdfField:
    def __init__(self, odb, step_name, field_name) -> None:
        self.odb = odb
        self.step_name = step_name
        self.field_name = field_name
        self.field = self.odb.steps[self.step_name].frames[-1].fieldOutputs[self.field_name]

        self.component_labels = (list(map(str, self.field.validInvariants))
                                 + list(self.field.componentLabels))

        position = self.field.locations[0].position
        if position == INTEGRATION_POINT:
            self.field = self.field.getSubset(position=CENTROID)
            self.field_name = self.field_name + " element result"

    def get_data(self):
        ids, values = [], []

        # 遍历所有节点的数据
        for value in self.field.values:
            node_id = value.nodeLabel
            ids.append(node_id)
            invariant_data = [self._getInvariantData(value, invariant_symbol)
                              for invariant_symbol in self.field.validInvariants]
            values.append(invariant_data + value.data.tolist())

        result = {
            "variables": self.component_labels,
            "type": "translation",
            "id": {
                "__isRecord__": True,
                "__dims__": [len(ids)],
                "__data__": ids if ids[0] is not None else list(range(1, len(ids) + 1))
            },
            "value": {
                "__isRecord__": True,
                "__dims__": [len(ids), len(values[0])],
                "__data__": values
            }
        }
        return result

    def _getInvariantData(self, value, invariant_symbol):
        if invariant_symbol == MAGNITUDE:
            return value.magnitude
        elif invariant_symbol == MISES:
            return value.mises
        elif invariant_symbol == TRESCA:
            return value.tresca
        elif invariant_symbol == PRESS:
            return value.press
        elif invariant_symbol == INV3:
            return value.inv3
        elif invariant_symbol == MAX_PRINCIPAL:
            return value.maxPrincipal
        elif invariant_symbol == MID_PRINCIPAL:
            return value.midPrincipal
        elif invariant_symbol == MIN_PRINCIPAL:
            return value.minPrincipal
        elif invariant_symbol == MAX_INPLANE_PRINCIPAL:
            return value.maxInPlanePrincipal
        elif invariant_symbol == MIN_INPLANE_PRINCIPAL:
            return value.minInPlanePrincipal
        elif invariant_symbol == OUTOFPLANE_PRINCIPAL:
            return value.outOfPlanePrincipal

class ZdfStep:
    def __init__(self, odb, step_name) -> None:
        self.odb = odb
        self.step_name = step_name
        self.fields = []
        # 构建field对象
        for field_name in self.odb.steps[self.step_name].frames[-1].fieldOutputs.keys():
            self.fields.append(ZdfField(self.odb, self.step_name, field_name))
    
    def get_data(self):
        result = {
            "step" : self.odb.steps[self.step_name].number,
            "time_value" : 1.0,
        }
        result.update({field.field_name : field.get_data() for field in self.fields})
        return result

class ZdfItems:
    def __init__(self, odb) -> None:
        self.odb = odb
        self.step_names = self.odb.steps.keys()
        self.steps = []
        for step_name in self.step_names:
            if len(self.odb.steps[step_name].frames) > 0:
                self.steps.append(ZdfStep(self.odb, step_name))

    def get_data(self):
        return {step.step_name : step.get_data() for step in self.steps}


class ZdfGlobal:
    def __init__(self, odb_file_path) -> None:
        self.model_name = os.path.basename(odb_file_path).split(".")[0]
        self.odb = odbAccess.openOdb(odb_file_path)
        self.items = ZdfItems(self.odb)
        self.model_mesh = ZdfModelMesh(self.odb)

    def get_data(self):
        global_template = {
            "header": {
                "version": 1.0,
                "date": f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
                "org": "ZWSoft",
                "author": "",
                "model": self.model_name,
                "version_digest": "1.0.0,VERNUM:04/29/2022(9485:eccfecd9f9e4)",
                "customize_prefix" : "zw_",
                "zw_app": "ZW3D",
            },
            "global" : {
                "units" : {
                    "mass" : "Kilogram",
                    "length" : "Meter",
                    "time" : "Second",
                    "temperature" : "Kelvin",
                    "electric_current" : "Ampere",
                    "substance_amount" : "Mole",
                    "luminous_intensity" : "Candela",
                    "angle" : "Radian",
                }
            },
            "model": {
                "mesh" : self.model_mesh.get_data()
            },
            "result_sets" : {
                os.path.basename(self.model_name).split(".")[0] : {
                    "analysis" : 1,
                    "items" : self.items.get_data()
                }
            }
        }
        return global_template


if __name__ == "__main__":
    odb_file = sys.argv[1]
    zdf_file = sys.argv[2]
    # odb_file_path = "D:\\temp\\Job-12.odb"

    data = ZdfGlobal(odb_file).get_data()

    with open(zdf_file, "w") as f:
        json.dump(data, f, indent=2)
