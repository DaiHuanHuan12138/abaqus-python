import odbAccess
import json
import time
import os

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
    
class ZdfModelMesh:
    def __init__(self, odb) -> None:
        self.odb = odb

        # 获取所有节点的id和坐标
        nodes = self.odb.rootAssembly.nodeSets[" ALL NODES"].nodes
        self.node_ids = []
        self.coordinates = []
        for node in nodes:
            self.node_ids.append(node.label)
            self.coordinates.append(node.coordinates)
        
        # 获取所有单元的id和连接性
        elements = self.odb.rootAssembly.elementSets[" ALL ELEMENTS"].elements
        self.element_ids = []
        self.connectivties = []
        for element in elements:
            self.element_ids.append(element.label)
            self.connectivties.append(element.connectivity)
  

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
    def __init__(self, odb, field_name) -> None:
        self.odb = odb
        self.field_name = field_name

    def get_data(self):
        ids = []
        values = []

        # 遍历所有节点的数据
        for value in self.odb.steps[step_name].frames[-1].fieldOutputs[self.field_name].values:
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
        for field_name in self.odb.steps[step_name].frames[-1].fieldOutputs.keys():
            self.fields.append(ZdfField(self.odb, field_name))
    
    def get_data(self):
        result = {
            "step" : self.odb.steps[step_name].number,
            "time_value" : 1.0,
        }
        result.extend({field.name : field.get_data() for field in self.fields})
        return result

class ZdfItems:
    def __init__(self, step_name, time_value, fields) -> None:
        self.step_name = step_name
        self.time_value = time_value
        self.fields = fields

    def get_data(self):
        result = {
            "step" : self.step_name,
            "time_value" : self.time_value,
            "fields" : self.fields
        }
        return result


class ZdfGlobal:
    def __init__(self, odb_file_path) -> None:
        self.odb = odbAccess.openOdb(odb_file_path)
        # 获取字符串形式的step的名字
        self.step_names = self.odb.steps.keys()

        self.steps = None
        self.model_mesh = None

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
                        self.steps.get_data()
                    }
                }
            }
        }
 
        

# 所有数据的提取类
class DataExtractor:
    def __init__(self, odb_file_path) -> None:
        self.odb = odbAccess.openOdb(odb_file_path)
        # 获取字符串形式的step的名字
        self.step_names = self.odb.steps.keys()

        self.global_template = {
            "headers": {
                "version": "1.0",
                "date": f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
                "org": "ZWSoft",
                "author": "",
                "model": "Undefined",
                "version_digest": "",
                "zw_app": "ZW3D",
            },
            "model": {
                "mesh" : {
                    "nodes" : {
                        "id": {
                            "__isRecord__": "true",
                            "__dims__": [],
                            "__data__": []
                        },
                        "coordinates": {
                            "__isRecord__": "true",
                            "__dims__": [],
                            "__data__": []
                        }
                    }
                }
            },
            "result_sets" : {
                os.path.basename(odb_file_path).split(".")[0] : {
                    "analysis" : 1,
                    "items" : {
                        # a lot of fields
                    }
                }
            }
        }

        self.step_template = {
            "step" : "step idx 1, 2, 3...",
            "time_value" : 1.0,
            # a lot of fields ...
        }
        self.field_template = {
            "variables" : [],
            "type": "field type",
            "id": {
                "__isRecord__": "true",
                "__dims__": [],
                "__data__": []
            },
            "value": {
                "__isRecord__": "true",
                "__dims__": [],
                "__data__": []
            }
        }

    def _extract_field_data(self, field, transformer):
        ids = []
        values = []

        # 遍历所有节点的数据
        for value in field.values:
            node_id = value.nodeLabel
            data = value.data  # 获取 x, y, z 分量

            ids.append(node_id)
            values.append(transformer(data))

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

    def _extract_step_data(self, step_name):
        step_data = {}
        for name, filed in self.odb.steps[step_name].frames[-1].fieldOutputs.items():
            if name in ["CF", "RF", "U"]:
                step_data[name] = self._extract_field_data(filed, TotalTransformer())
            else:
                step_data[name] = self._extract_field_data(filed, NaiveTransformer())
        return step_data
    
    def _extract_nodes(self):
        nodes = self.odb.rootAssembly.nodeSets[" ALL NODES"].nodes
        ids = []
        coordinates = []

        for node in nodes:
            ids.append(node.label)
            coordinates.append(node.coordinates)
        
        result = {
            "id": {
                "__isRecord__": "true",
                "__dims__": [len(ids)],
                "__data__": ids
            },
            "coordinates": {
                "__isRecord__": "true",
                "__dims__": [len(ids), 3],
                "__data__": coordinates
            }
        }
        return result

    def _extract_elements(self):
        elements = self.odb.rootAssembly.elementSets[" ALL ELEMENTS"].elements
        ids = []
        connectivties = []
        for element in elements:
            ids.append(element.label)
            connectivties.append(element.connectivity)
        
        result = {
            "id": {
                "__isRecord__": "true",
                "__dims__": [len(ids)],
                "__data__": ids
            },
            "connectivity": {
                "__isRecord__": "true",
                "__dims__": [len(ids), len(connectivties[0])],
                "__data__": connectivties
            }
        }
        return result
    
    def _extract_headers(self):
        header = {
            "version": "1.0",
            "date" : f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
            "org": "ZWSoft",
            "author": "",
            "model": "Undefined",
            "version_digest": "",
            "zw_app": "ZW3D",
        }
        return header
    
    def extract_part_data(self):
        result = {}

        step_data = {}
        for step_name in self.step_names:
            step_data[step_name] = self._extract_step_data(step_name)

        result["steps"] = step_data

        return result

    def extract_mesh(self):
        result = {}
        result["nodes"] = self._extract_nodes()
        result["elements"] = self._extract_elements()
        return result

    def extract_all_data(self):
        result = {}

        step_data = {}
        for step_name in self.step_names:
            step_data[step_name] = self._extract_step_data(step_name)

        result["headers"] = self._extract_headers()
        result["model"] = {}
        result["model"]["mesh"] = self.extract_mesh()
        
        result_sets = {
            " " : {
                "analysis" : 1, 
            }
        }
        

        return result


# 使用示例
odb_file_path = "D:\\temp\\Job-2.odb"
step_name = "Step-1"

data_extractor = DataExtractor(odb_file_path)

data = data_extractor.extract_part_data()
print(data)

with open("data.json", "w") as f:
    json.dump(data, f, indent=2)


# odb = odbAccess.openOdb(odb_file_path)
# print(odb.steps[step_name].frames[-1].fieldOutputs["CF"])
# for data in odb.rootAssembly.nodeSets.keys():
#     print(data)
#     break
