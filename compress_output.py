"""将 output 目录打包为 zip，并保存在该目录内。"""

import os
import zipfile
from datetime import datetime


def compress_output_dir(output_dir: str = "output") -> str:
    """
    将 output_dir 整目录打包为 zip，zip 文件保存在该目录下。

    返回生成的 zip 绝对路径。
    """
    base = os.path.abspath(output_dir)
    os.makedirs(base, exist_ok=True)
    parent = os.path.dirname(base)

    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"output_archive.zip"
    zip_path = os.path.join(base, zip_name)
    zip_abs = os.path.abspath(zip_path)

    # 判断文件是否存在，并且是文件（不是文件夹）
    if os.path.isfile(zip_abs):
        os.remove(zip_abs)
        print(f"文件 {zip_abs} 已删除")
    else:
        print(f"文件 {zip_abs} 不存在")

    with zipfile.ZipFile(zip_abs, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(base):
            for name in files:
                filepath = os.path.join(root, name)
                if os.path.abspath(filepath) == zip_abs:
                    continue
                arcname = os.path.relpath(filepath, parent)
                zf.write(filepath, arcname)

    print(f"output 目录已压缩: {zip_abs}")
    return zip_abs


def main(output_dir: str = "output") -> str:
    return compress_output_dir(output_dir)


if __name__ == "__main__":
    main()
