# PISL集成光子器件和系统gds
PISL_PDK.py暂时存放所有需要用的光子器件的函数

## 文件说明
1. 20220710-T1PEISL-cwy.py/20220710-T1PEISL-cwy.gds（**已加工**）：用于确定工艺参数
2. 20220926-G1PEISL-cwy.py/20220926-G1PEISL-cwy.gds：用于测试grating coupler耦合效率以及波导损耗
3. layerset.gds：layer层定义（引用自gdsfactory层定义）
4. test.py以及test.gds用于测试函数

## 文件名规定
除PDK外所有py文件和gds文件名称定义为：时间-文件名-人名.py 和 时间-文件名-人名.gds  
（同一个py文件以及对应的gds文件 文件名称必须相同）
例：20220701-T1PEISL-cwy.py和20220701-T1PEISL-cwy.gds


