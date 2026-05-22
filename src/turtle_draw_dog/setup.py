from glob import glob
from setuptools import find_packages, setup

package_name = "turtle_draw_dog"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/assets", glob("assets/*")),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
        (f"share/{package_name}/docs", glob("docs/*")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Inteli",
    maintainer_email="inteli@example.com",
    description="Desenha contornos de uma imagem no turtlesim usando ROS 2.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "draw_dog = turtle_draw_dog.draw_dog:main",
            "preview_pipeline = turtle_draw_dog.preview_pipeline:main",
        ],
    },
)
