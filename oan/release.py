"""The data release: a version label and a content hash over every data file.

data/RELEASE holds two lines, "data_version=..." and "content_sha256=...". The hash covers
every file under data/ except RELEASE, in sorted path order (path and bytes), so any edit
changes it. The release step writes RELEASE; every Result carries both values.
"""

import hashlib
import os


def content_hash(data_dir):
    h = hashlib.sha256()
    paths = []
    for dirpath, _, files in os.walk(data_dir):
        for f in files:
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, data_dir).replace(os.sep, "/")
            if rel != "RELEASE":
                paths.append((rel, path))
    for rel, path in sorted(paths):
        with open(path, "rb") as f:
            data = f.read()
        h.update(rel.encode("utf-8") + b"\0" + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()


def read_release(data_dir):
    out = {}
    with open(os.path.join(data_dir, "RELEASE"), encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                out[k] = v
    return out


def write_release(data_dir, version):
    with open(os.path.join(data_dir, "RELEASE"), "w", encoding="utf-8", newline="\n") as f:
        f.write("data_version=%s\ncontent_sha256=%s\n" % (version, content_hash(data_dir)))
