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
class ZdfModelMesh:
    def __init__(self, odb) -> None:
        self.odb = odb

        # 获取所有节点的id和坐标
        nodes = self.odb.rootAssembly.nodeSets[" ALL NODES"].nodes
        self.node_ids = []
        self.coordinates = []
        for node in nodes:
            self.node_ids.append(node.label)
            self.coordinates.append(list(node.coordinates))
        
        # 获取所有单元的id和连接性
        elements = self.odb.rootAssembly.elementSets[" ALL ELEMENTS"].elements
        self.element_ids = []
        self.connectivties = []
        for element in elements:
            self.element_ids.append(element.label)
            self.connectivties.append(list(element.connectivity))


    def get_data(self):
        result = {
            "nodes" : {
                "id": {
                    "__isRecord__": "true",
                    "__dims__": [len(self.node_ids)],
                    "__data__": self.node_ids
                },
                "coordinates": {
                    "__isRecord__": "true",
                    "__dims__": [len(self.node_ids), len(self.node_coordinates[0])],
                    "__data__": self.node_coordinates
                }
            },
            "elements" : {
                "id": {
                    "__isRecord__": "true",
                    "__dims__": [len(self.element_ids)],
                    "__data__": self.element_ids
                },
                "coordinates": {
                    "__isRecord__": "true",
                    "__dims__": [len(self.element_ids), len(self.element_connectivities[0])],
                    "__data__": self.element_connectivities
                }
            }
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
                values.append(TotalTransformer(data))
            else:
                values.append(NaiveTransformer(data))

        result = {
            "id": {
                "__isRecord__": "true",
                "__dims__": [len(ids)],
                "__data__": ids
            },
            "value": {
                "__isRecord__": "true",
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
        result.extend({field.name : field.get_data() for field in self.fields})
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
        self.odb = odbAccess.openOdb(odb_file_path)

        self.items = ZdfItems(self.step_names, 1.0, self.fields)
        self.model_mesh = ZdfModelMesh(self.odb)

    def get_data(self):
        global_template = {
            "headers": {
                "version": 1.0,
                "date": f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
                "org": "ZWSoft",
                "author": "",
                "model": "Undefined",
                "version_digest": "",
                "zw_app": "ZW3D",
            },
            "model": {
                "mesh" : self.model_mesh.get_data()
            },
            "result_sets" : {
                os.path.basename(odb_file_path).split(".")[0] : {
                    "analysis" : 1,
                    "items" : {
                        self.items.get_data()
                    }
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
