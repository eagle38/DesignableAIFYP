

from roboflow import Roboflow
rf = Roboflow(api_key="NT7lGm2FSIulIG3KWgeQ")
project = rf.workspace("designableai").project("designableai-miotn")
version = project.version(3)
dataset = version.download("yolov5")
                