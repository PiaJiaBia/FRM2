"""网页结果索引标签独立于用户可自由命名的数据列。"""


def index_columns(frame, labels):
    """保留每层索引，同时避免索引标签覆盖或撞上现有列名。"""
    occupied = {str(column) for column in frame.columns}
    names = []
    for label in labels:
        while label in occupied:
            label = '_' + label
        names.append(label)
        occupied.add(label)
    return frame.reset_index(names=names)
