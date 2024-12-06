import odbAccess
import json
import time
import os

#==============================================================================#
class NaiveTransformer:
    """
    一个简单的转换器，不做任何处理
    """
    def __call__(self, data):
        return data.tolist()
    
class TotalTransformer:
    """
    一个简单的转换器，将 x, y, z 三个分量转换为总量, 并将总量和分量一起返回
    """
    def __call__(self, data):
        data = data.tolist()
        total = (data[0]**2 + data[1]**2 + data[2]**2)**0.5
        return [data[0], data[1], data[2], total]

#==============================================================================#

class ZdfElement:
    def __init__(self, odb):
        self.odb = odb

    @classmethod
    def _abaqus_type_2_zdf_type(cls, aba_type):
        if aba_type[:3] != "C3D":
            return ("ERROR", -1)
        node_num = ""
        for c in aba_type[3:]:
            if c.isdigit():
                node_num += c
            else:
                break
        return ("hexa8", 29)


    def get_data(self):
        elements = self.odb.rootAssembly.elementSets[" ALL ELEMENTS"].elements[0]
        type2 = {}
        for element in elements:
            zdf_type, type_id = self._abaqus_type_2_zdf_type(element.type)
            if zdf_type in type2:
                type2[zdf_type]["id"]["__data__"].append(element.label)
                type2[zdf_type]["value"]["__data__"].append(list(element.connectivity))
            else:
                type2[zdf_type] = {
                    "type id": type_id,
                    "id" : {
                        "__isRecord__": True,
                        "__dimes__": [],
                        "__data__": []
                    },
                    "value": {
                        "__isRecord__": True,
                        "__dims__": [],
                        "__data__": []
                    }
                }
        for key in type2:
            type2[key]["id"]["__dims__"] = [len(type2[key]["id"]["__data__"])]
            type2[key]["value"]["__dims__"] = [len(type2[key]["value"]["__data__"]), len(type2[key]["value"]["__data__"][0])]

        return type2

class ZdfModelMesh:
    def __init__(self, odb) -> None:
        self.odb = odb

        # 获取所有节点的id和坐标
        nodes = self.odb.rootAssembly.nodeSets[" ALL NODES"].nodes[0]
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
                    "__data__": self.node_ids
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

    def get_data(self):
        ids = []
        values = []

        # 遍历所有节点的数据
        for value in self.odb.steps[self.step_name].frames[-1].fieldOutputs[self.field_name].values:
            node_id = value.nodeLabel
            data = value.data
            ids.append(node_id)
            if self.field_name in ["CF", "RF", "U"]:
                values.append(TotalTransformer()(data))
            else:
                values.append(NaiveTransformer()(data))

        result = {
            "id": {
                "__isRecord__": True,
                "__dims__": [len(ids)],
                "__data__": ids
            },
            "value": {
                "__isRecord__": True,
                "__dims__": [len(ids), len(values[0])],
                "__data__": values
            }
        }
        return result

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
        self.steps = [ZdfStep(self.odb, step_name) for step_name in self.step_names]

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
            "headers": {
                "version": 1.0,
                "date": f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
                "org": "ZWSoft",
                "author": "",
                "model": self.model_name,
                "version_digest": "",
                "zw_app": "ZW3D",
            },
            "model": {
                "mesh" : self.model_mesh.get_data()
            },
            "result_sets" : {
                os.path.basename(odb_file_path).split(".")[0] : {
                    "analysis" : 1,
                    "items" : self.items.get_data()
                }
            }
        }
        return global_template


# 使用示例
odb_file_path = "D:\\temp\\Job-2.odb"
step_name = "Step-1"

data = ZdfGlobal(odb_file_path).get_data()

with open("data.json", "w") as f:
    json.dump(data, f, indent=2)
