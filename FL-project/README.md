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
git submodule update --init --recursive

# init defects4j
cd defects4j && ./init.sh && cd .. 

# create venv and install python3 packages
python3.6 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

# Run
假设实验生成的 gzoltars 数据位于 *./data/gzoltars* 目录下。
```bash
# 提取 features 文件, 输出到 ./data/feature_lists 目录下
.venv/bin/python3 abstract_featurelist.py -d ./data/gzoltars/ -o ./data/feature_lists

# 使用 features 文件，对每个 bug 计算 ranklist, 输出到 ./data/rank_lists 目录下
.venv/bin/python3 ranklist.py -f ./data/feature_lists/ -o ./data/rank_lists

# 对生成的 ranklist 计算 metric
.venv/bin/python3 metric.py data/rank_lists/ -t 
```
