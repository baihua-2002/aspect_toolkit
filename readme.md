# 编写ASPECT参数配置文件(.prm)的智能体
## connector模块：与ASPECT交互

* 屏蔽系统差异
* 运行指定的`.prm`文件，获得结果

## 查询文档 RAG系统
* 已实现：参数检索 + 专家案例检索（统一入口）
* 详见 [RAG/readme.md](RAG/readme.md)

```
RAG/
├── parameter_searcher.py    # 参数检索器（1594 条 ASPECT 参数定义）
├── case_searcher.py         # 专家案例检索器（文献清洗，待填充）
├── rag.py                   # 统一入口 AspectRAG
├── parameters.json          # 参数定义数据源
└── cases.json               # 专家案例数据源（空模板）
```
## PRM parser
* 从语法树生成aspect prm

## MVP


```
通用大模型
+ ASPECT 官方文档和示例的版本化检索
+ tree-sitter 风格或自定义 PRM parser
+ JSON Schema/参数目录
+ 静态规则检查器
+ 生成-运行-修复循环
+ 专家审核界面
```
