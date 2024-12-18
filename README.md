# Introduction
Abaqus是一款著名的有限元仿真模拟软件。ZWSim要支持将Abaqus的仿真结果导入到ZWSim中，以便于用户在ZWSim中进行后续的仿真分析。

Abaqus将仿真模拟结果保存在.odb文件中，这个文件包括了仿真模拟的所有信息，包括了节点的坐标，单元的信息，单元的应力应变等。
我们需要编写脚本从.odb文件中读取这些信息，并将这些信息转换为ZWSim的数据结构。

ZWSim使用一个.zdf文件来保存仿真模拟的信息。这个文件使用json格式记录了仿真模拟的信息，
其结构可以参照本目录下的`example.zdf`文件。

首先，.zdf文件包括了header和global两个部分。 header主要记录了版本、日期、作者等信息。global记录了单位信息。
这两部分的内容都是固定的(日期除外)，不需要改变。

然后，.zdf文件还有一个model字段，包括mesh的节点和单元的信息，比如：
```
{
  "model": {
    "mesh": {
      "nodes": { # 节点信息
        "id": { # 节点的id信息
          "__isRecord__": true, # 固定信息，不需要改变
          "__dims__": [
            2767 # dims记录了__data__数组的形状，这里是2767个节点
          ],
          "__data__": [1, 2, 3, 4, 5, 6, 7, 8, .....] # 节点的id信息
        },
        "value": {
          "__isRecord__": true,
          "__dims__": [
            2767, # dims记录了__data__数组的形状，这里是2767个节点
            3 # 每个节点有 xyz 3个坐标
          ],
          "__data__": [
            [-50.0,-25.0,2.0],
            [-50.0,25.0,2.0],
            [-50.0,25.0,0.0],
            [-50.0,-25.0,0.0],
            [50.0,25.0,2.0], 
            ......
          ]
        }
      },
      "elements": { # 单元信息
        "tetra10": { # tetra10是一个element type
          "type id": 28,
          "id": {
            "__isRecord__": true,
            "__dims__": [
              1342 # dims记录了__data__数组的形状，这里是1342个单元
            ],
            "__data__": [1, 2, 3, 4, 5, 6, 7, 8, .....] # 单元的id信息
          },
          "value": {
            "__isRecord__": true,
            "__dims__": [
              1342, # dims记录了__data__数组的形状，这里是1342个单元
              10 # 每个单元有10个节点
            ],
            "__data__": [
              [463,443,123,142,484,485,486,487,488,489],
              [321,464,250,320,490,491,492,493,494,495],
              [144,426,465,417,496,497,498,499,500,501],
              [51,40,354,39,502,503,504,505,506,507],
              ......
            ]
          }
        }
      }
    }
  }
}
```

最后是result_sets字段，包括很多个step， step包括了多种仿真模拟的结果信息。每种结果信息称为一个field。比如，displacement就是一个field。
在ZWSim中，一个field要么是作用在节点上的，要么是作用在单元上的。

比如说，节点的位移，节点的速度，节点的加速度等是作用在节点上的；单元的应力，单元的应变等是作用在单元上的。
如果一个field的名字中包括了"element result"，那么这个field是作用在单元上的，否则是作用在节点上的。

下面是result_sets字段的一个例子：
```
{
  "result_sets": {  // 结果信息
    "Job-12": { // Job-12是一个job的名字
      "analysis": 1, // 固定信息，不需要改变
      "items": { // items包括了很多个step
        "Step-1": { // Step-1是一个step的名字
          "step": 1, // 该step的序号
          "time_value": 1.0, // 固定信息，不需要改变
          "S element result": { // S element result是一个field的名字，这个field是作用在单元上的
            "variables": [
              // 一个field包括多个变量，这里指定了这个field包括哪些变量
              "MISES",
              "MAX_PRINCIPAL",
              "MID_PRINCIPAL",
              "MIN_PRINCIPAL",
              "TRESCA",
              "PRESS",
              "INV3",
              "S11",
              "S22",
              "S33",
              "S12",
              "S13",
              "S23"
            ],
            "type": "translation",  // 固定信息，不需要改变
            "id": { // 单元的id信息
              "__isRecord__": true,
              "__dims__": [
                1342
              ],
              "__data__": [1, 2, 3, 4, 5, 6, 7, 8, .....]
            },
            "value": {  // 每个单元上的field的值
              "__isRecord__": true,
              "__dims__": [
                1342,
                13
              ],
              "__data__": [
                // 这里的每个数值的含义在variables中被定义了
                [21305.21875,1116.1192626953125,201.9412841796875,-20631.47265625,21747.591796875,6437.80419921875,-21261.021484375,-19633.08203125,1111.441650390625,-791.772705078125,286.02362060546875,4441.7373046875,-34.70952606201172],
                ......
              ]
            }
          },
          "U": { // U是一个field的名字，这个field是作用在节点上的
            "variables": [
              "MAGNITUDE",
              "U1",
              "U2",
              "U3"
            ],
            "type": "translation",
            "id": {
              "__isRecord__": true,
              "__dims__": [
                2767
              ],
              "__data__": [1, 2, 3, 4, 5, 6, 7, 8, .....]
            },
            "value": {
              "__isRecord__": true,
              "__dims__": [
                2767,
                4
              ],
              "__data__": [
                [0.000305751571431756,-3.153933721478097e-05,8.28669362817891e-06,-0.0003040076117031276],
                [0.0003006964980158955,-3.1416107958648354e-05,-8.823793905321509e-06,-0.0002989206404890865],
                [0.0003005809267051518,3.129826291115023e-05,8.48021409183275e-06,-0.00029882669332437217],
                [0.00030585535569116473,3.157414903398603e-05,-8.628392606624402e-06,-0.00030409888131543994],
                ......
              ]
            }
          }
        }
      }
    }
  }
}
```

## python代码简介
`driver\ZwApp\Resource\ZwSimulationPlateform\supp\odb2zdf.py`是一个python脚本，用于将Abaqus的.odb文件转换为ZWSim的.zdf文件，其中包括多个类，
每个类都包括一个get_data方法，用于从.odb文件中读取数据。类的组织结构与前面提到的.zdf文件的结构相对应。

1. ZdfAllData类包括了所有的数据，包括了ZdfModelMesh和ZdfResultItems类的对象
(header和global信息是写死的，不需要为其创建类)。
2. ZdfResultItems：使用ZdfStep.get_data()提取了所有的step信息，包括多个ZdfStep类的对象。
3. ZdfStep：使用ZdfField.get_data()提取所有的field信息，包括多个ZdfField类的对象。
4. ZdfField：从odb对象中提取了field的值。
5. ZdfModelMesh：从odb对象中提取node信息；使用ZdfElement.get_data()提取了element信息。
6. ZdfElement：从odb对象中提取了element的信息。

## bat代码简介
`driver\ZwApp\Resource\ZwSimulationPlateform\supp\odb2zdf.bat`是一个批处理脚本，
用于调用`odb2zdf.py`脚本，将Abaqus的.odb文件转换为ZWSim的.zdf文件。
代码主要分为三部分。首先，需要判断用户的机器上是否安装了abaqus，如果没有安装，则退出程序并返回状态码2。
然后，使用abaqus python运行`odb2zdf.py`脚本，将.odb文件转换为.zdf文件。如果执行失败，则退出程序并返回状态码1。
最后，输出执行成功的信息，并返回状态码0。

```bat
where abaqus >nul 2>nul
if %errorlevel% neq 0 (
	echo abaqus python not found
	exit /b 2
)
:: abaqus python python_script odb_file zdf_file
:: %1 is the path to odb2zdf.py, %2 the path to odb file, %3 the path to zdf file to be output
abaqus python %1 %2 %3 :: 执行脚本，%1, %2, %3是.bat文件的参数
if %errorlevel% neq 0 (
	echo command execution failed
	exit /b 1
)
echo Command executed successfully
exit /b 0
```
odb2zdf.bat文件的需要三个参数，分别是`python_script`、`odb_file`和`zdf_file`。

## C++代码简介
C++代码位于`ZwOdbTranslator\src\ZwOdbTranslator.cpp`文件的ZwOdbTranslatorImp::ReadFile函数中，
用于将Abaqus的.odb文件转换为ZWSim的.zdf文件。
C++代码实际上相当简单,它首先获取python脚本、zdf文件和odb文件的路径，然后调用`odb2zdf.bat`脚本。
调用的方法是使用`system`函数，这个函数会调用系统的shell来执行命令。

system函数的返回值是命令的返回值，如果命令执行成功，返回值是0，否则是非0。
如果返回值是0，说明执行成功，那么我们执行下面两行代码：
```cpp
q->ZwZdfTranslator::ReadFile(zdf_file); // 读取文件中的mesh信息
q->GetZdfManager().resultPath = zdf_file; // 读取文件中的result信息
```


# Useful links
1. Abaqus Scripting User's Guide

    这个链接是Abaqus的官方文档，其中包括了Abaqus了如何使用Python脚本从.odb文件中读取数据。
    
    http://130.149.89.49:2080/v2016/books/cmd/default.htm

2. Element Type Naming Convention(命名规则)
    
    Abaqus和ZWSim都包括大量的Element Type。Element Type的名称中包括了很多信息，包括element的类型，节点数等。
    比如说，`C3D8`是Abaqus中的一个element type，字母`C`表示`continuum`，数字`3`表示element的节点数，`8`表示element的节点数。
    因此，根据命名规则从element type的名称中提取出element的信息是非常重要的。下面是一些有用的链接：
    
    下面两个链接是Abaqus的官方文档，其中包括了Abaqus的element type的命名规则。
    
    https://classes.engineering.wustl.edu/2009/spring/mase5513/abaqus/docs/v6.6/books/gss/default.htm?startat=ch03s01.html
    
    http://130.149.89.49:2080/v2016/books/usb/default.htm?startat=pt06ch29s03ael14.html
    
    下面是两个重要的ZwSim源代码文件，其中包括了ZwSim的element type的命名规则：
    
    `ZwZdfData/inc/head/ZwZdfMeshHead.h`
    这个文件包括了element type的枚举    

    `ZwZdfData/inc/api/ZwZdfMeshHeader.h`
    这个文件包括了element的形状信息

# TODO
1. 支持多个Part
2. 目前只支持Continuum和Beam Element，还需要支持其他Element
