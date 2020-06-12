# Requirements

+ Python3 >= 3.6.8
+ Oracle JDK 1.8
+ Git

For example, on ubuntu 14.04,

```bash
# install command line tools
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y git python3.6 python3.6-venv python3.6-dev
```
# Installation

```bash
# clone codes
git clone [this_project] /to/path

# init defects4j under FL-project
git clone [defcts4j] 
cd defects4j && ./init.sh && cd .. 

# create venv and install python3 packages
python3.6 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

# Data
使用 GZoltar 对 Defects4J 数据集进行实验收集的数据打包在 gzoltars.zip 文件中。

使用我们实现的 static-analyzer 工具抽取的语句依赖信息打包在 stmt_graph.zip 文件中。

这些 zip 文件可以解压到项目目录下的 data 文件夹下进行使用。
# Run
假设实验生成的 gzoltars 数据位于 *./data/gzoltars* 目录下。
```bash
# 提取 features 文件, 输出到 ./data/feature_lists 目录下
.venv/bin/python3 abstract_featurelist.py -d ./data/gzoltars/ -o ./data/feature_lists

# 使用 features 文件，对每个 bug 计算 ranklist, 输出到 ./data/rank_lists 目录下
.venv/bin/python3 ranklist.py -f ./data/feature_lists/ -o ./data/rank_lists

# 对生成的 ranklist 计算 metric
.venv/bin/python3 metric.py ./data/rank_lists/ -t 

# 使用数据依赖信息增强定位结果（-m 可取 ochiai,barinel,op2,dstar,tarantula）
.venv/bin/python3 transform.py -d ./data/stmt_graph -r ./data/rank_lists -o ./data/sa_rank_lists -m ochiai

# 对增强后的定位结果计算 metric
.venv/bin/python3 metric.py ./data/sa_rank_lists/ -t 
```
