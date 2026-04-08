# /// script
# dependencies = ["pyyaml"]
# requires-python = ">=3.12"
# ///

from __future__ import annotations

import json
import re
import sys
from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

import yaml

type JsonData = dict[str, JsonData | str]


class Entry(NamedTuple):
    key: tuple[str, ...]
    value: str


class FlatEntry(NamedTuple):
    key: str
    value: str


# region yaml配置
def custom_str_presenter(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')

    elif data.lstrip().startswith(('[', '{', '-', '#', '*', '&', '!', '>', '<', '%', '@', '`', '"', "'")):
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')

    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


yaml.add_representer(str, custom_str_presenter)
yaml.representer.SafeRepresenter.add_representer(str, custom_str_presenter)


# endregion yaml配置

# region 辅助函数
def extract_entries(data: JsonData, current_path: tuple[str, ...] = ()) -> list[Entry]:
    """递归遍历嵌套字典，生成一维的 Entry 列表"""
    entries: list[Entry] = []

    for k, v in data.items():
        new_path = current_path + (k,)
        if isinstance(v, dict):
            # 如果是字典，递归提取并展平合并
            entries.extend(extract_entries(v, new_path))
        elif isinstance(v, str):
            # 如果是字符串，直接构造 Entry
            entries.append(Entry(new_path, v))
        else:
            # 防御性编程：虽然你保证了只有 dict 和 str，但最好还是抛出明确的异常
            raise TypeError(f"发现不支持的类型: {type(v)} 于路径 {new_path}")

    return entries


def restore_json(entries: Iterable[Entry]) -> JsonData:
    """根据 tuple 路径，重新构建嵌套字典"""
    root: JsonData = {}

    for entry in entries:
        if not entry.key:
            continue

        current_node: JsonData = root

        # 遍历路径，除了最后一个节点（用来建嵌套字典）
        for part in entry.key[:-1]:
            if part not in current_node:
                current_node[part] = {}

            next_node = current_node[part]
            # 冲突检测：防止同一路径既被当做字典又被当做字符串
            if not isinstance(next_node, dict):
                raise ValueError(f"路径冲突：节点 '{part}' 已经被赋值为字符串，无法作为字典使用。")

            current_node = next_node

        # 最后一个节点赋值为字符串
        leaf_key = entry.key[-1]
        if leaf_key in current_node and isinstance(current_node[leaf_key], dict):
            raise ValueError(f"路径冲突：节点 '{leaf_key}' 已存在子字典，无法赋值为字符串。")

        current_node[leaf_key] = entry.value

    return root


def pascal_to_upper_snake(name: str) -> str:
    if not name:
        return name
    s1 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    return s1.upper()


def upper_snake_to_pascal(name: str) -> str:
    if not name:
        return name
    return "".join(word.capitalize() for word in name.split("_"))


def yaml_to_entries(path: Path) -> list[Entry]:
    with open(path, 'r', encoding='utf-8-sig') as f:
        data = yaml.safe_load(f)
    entries = extract_entries(data)
    return entries


def entries_to_yaml(path: Path, entries: Iterable[Entry]) -> None:
    data = restore_json(entries)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            default_flow_style=False,  # 强制块状风格
            sort_keys=False,  # 保持字典原有的顺序 (Python 3.7+ 字典是有序的)
            width=float("inf")  # 禁用 PyYAML 的自动折行，防止强行切断长文本并产生多余空行
        )


def json_to_flat_entries(path: Path) -> list[FlatEntry]:
    with open(path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    return [FlatEntry(k, v) for k, v in data.items()]


def flat_entries_to_json(path: Path, entries: Iterable[FlatEntry]) -> None:
    data = {k: v for k, v in entries}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=4, sort_keys=False)


# endregion

# region 格式化器
class Formatter(ABC):
    def forward(self, entry: Entry) -> FlatEntry:
        result = self.forward_key(entry.key)
        assert entry.key == self.backward_key(result)
        return FlatEntry(result, entry.value)

    def backward(self, flat_entry: FlatEntry) -> Entry:
        result = self.backward_key(flat_entry.key)
        assert flat_entry.key == self.forward_key(result)
        return Entry(result, flat_entry.value)

    @abstractmethod
    def forward_key(self, key: tuple[str, ...]) -> str:
        ...

    @abstractmethod
    def backward_key(self, key: str) -> tuple[str, ...]:
        ...


class DotFormatter(Formatter):
    def forward_key(self, key: tuple[str, ...]) -> str:
        return ".".join(key)

    def backward_key(self, key: str) -> tuple[str, ...]:
        return tuple(key.split("."))


class ModelFormatter(Formatter):
    def __init__(self, pos=0):
        self.pos = pos

    def forward_key(self, key: tuple[str, ...]) -> str:
        l = list(key)
        if l[self.pos].startswith("$"):
            l[self.pos] = l[self.pos][1:]
        else:
            l[self.pos] = PREFIX + pascal_to_upper_snake(l[self.pos])
        return ".".join(l)

    def backward_key(self, key: str) -> tuple[str, ...]:
        l = key.split(".")
        if l[self.pos].startswith(PREFIX):
            l[self.pos] = upper_snake_to_pascal(l[self.pos][len(PREFIX):])
        else:
            l[self.pos] = "$" + l[self.pos]
        return tuple(l)


# endregion

# region 配置区

SCRIPT_PATH = Path(__file__)  # 脚本路径
PROJECT_ROOT = SCRIPT_PATH.parent.parent.parent  # 项目根路径
JSON_LOC_ROOT = PROJECT_ROOT / 'ExampleMod' / 'localization'  # json 本地化路径
YAML_LOC_ROOT = SCRIPT_PATH.parent  # yaml 本地化路径
LOC_LIST = ['zhs']  # 支持的语言
# 使用的本地化表和格式化器
# DotFormatter：普通的依据点分割
# ModelFormatter：智能处理 ModelId（PascelCase 与 UPPER_SNAKE_CASE 互转，并自动添加/去除 BaseLib 前缀）。pos 为 ModelId 的位置，默认为 0。
NORMAL_TABLES = {
    'cards': ModelFormatter(),      # ModelId 为按点分割后的第一部分，故 pos 为 0（默认值）
    'ancients': ModelFormatter(2),  # ModelId 为按点分割后的第一部分，故 pos 为 2
    'gameplay_ui': DotFormatter(),  # 不涉及 ModelId，直接用 DotFormatter 处理
}
PREFIX = "EXAMPLEMOD" + "-"  # 如果使用 BaseLib 的 Custom 系列，在这里写前缀，否则写空字符串。
# REMOVE_THIS_AFTER_FINISH_CONFIGURATION = 42  # 配置结束后，将这行代码移除。


# endregion

# json 转 yaml
def main_backward():
    for loc in LOC_LIST:
        json_loc_dir = JSON_LOC_ROOT / loc
        yaml_loc_dir = YAML_LOC_ROOT / loc
        for table, fmt in NORMAL_TABLES.items():
            if not (json_loc_dir / f"{table}.json").exists():
                print(f"警告：{json_loc_dir / f'{table}.json'} 不存在，跳过。")
                continue
            flat_entries = json_to_flat_entries(json_loc_dir / f"{table}.json")
            entries = [fmt.backward(fe) for fe in flat_entries]
            entries_to_yaml(yaml_loc_dir / f"{table}.yaml", entries)


# yaml 转 json
def main_forward():
    for loc in LOC_LIST:
        json_loc_dir = JSON_LOC_ROOT / loc
        yaml_loc_dir = YAML_LOC_ROOT / loc
        for table, fmt in NORMAL_TABLES.items():
            if not (yaml_loc_dir / f"{table}.yaml").exists():
                print(f"警告：{yaml_loc_dir / f'{table}.yaml'} 不存在，跳过。")
                continue
            entries = yaml_to_entries(yaml_loc_dir / f"{table}.yaml")
            flat_entries = [fmt.forward(e) for e in entries]
            flat_entries_to_json(json_loc_dir / f"{table}.json", flat_entries)


if __name__ == '__main__':
    if "REMOVE_THIS_AFTER_FINISH_CONFIGURATION" in globals():
        print("请先完成配置。如果已完成，移除掉配置区的最后一行代码。")
        sys.exit(-1)
    print(f"脚本路径为：{SCRIPT_PATH}")
    print(f"Json 本地化路径为：{JSON_LOC_ROOT}")
    print(f"Yaml 本地化路径为：{YAML_LOC_ROOT}")
    match input("你想要：\n1. Yaml 转 Json\n2. Json 转 Yaml\n3. 退出\n请输入数字：").strip():
        case "1":
            main_forward()
            print("转换完成！")
        case "2":
            main_backward()
            print("转换完成！")
        case "3":
            print("退出程序。")
        case _:
            print("无效输入，退出程序。")
