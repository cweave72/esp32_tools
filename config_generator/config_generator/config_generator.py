import os.path as osp
import shutil
import sys
import click
import logging
import importlib
import yaml
from pathlib import Path
from rich import inspect

import pkg_resources
import grpc_tools.protoc as protoc

from config_generator import setup_logging

logger = logging.getLogger(__name__)

thisdir = osp.dirname(__file__)
libdir = osp.join(thisdir, 'lib')


def config_build(proto_path, includes):
    """Builds the python api locally.
    """
    if not isinstance(includes, list):
        includes = [includes]

    proto_include = pkg_resources.resource_filename("grpc_tools", "_proto")

    fmt_includes = [f"-I{proto_include}"]
    fmt_includes += [f"-I{inc}" for inc in includes]
    cmd_str = fmt_includes + [f"--python_betterproto_out={libdir}"] + [proto_path]

    logger.debug(f"Cleaning dir: {libdir}")
    shutil.rmtree(libdir)
    Path(libdir).mkdir()

    logger.debug(f"cmd_str = {cmd_str}")
    try:
        ret = protoc.main(cmd_str)
        if ret == 1:
            logger.error("Error: protoc returned error.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error in grpc_tools.main(): {str(e)}")
        sys.exit(1)


def config_write(mod_name, cls_name, data, out):

    logger.debug(f"module name={mod_name}; class={cls_name}")

    if mod_name is not None:
        mod = importlib.import_module(f"config_generator.lib.{mod_name}")
    else:
        mod = importlib.import_module("config_generator.lib")

    try:
        cls = getattr(mod, cls_name)
        inst = cls()
        inst.from_dict(data)
        #inspect(inst)
        logger.info(f"Protobuf message: {inst.to_dict()}")
        serialized = inst.SerializeToString()
    except Exception as e:
        logger.exception(f"Error loading dataclass: {str(e)}")
        sys.exit(1)

    outfile = Path(out)
    outfile.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Writing {outfile.absolute()}")
    with outfile.open('wb') as f:
        f.write(serialized)


@click.group()
@click.option("--loglevel", default='info', help="Debug logging level.")
@click.pass_context
def cli(ctx, loglevel):

    rlogger = logging.getLogger()
    setup_logging(rlogger, level=loglevel)


@cli.command
@click.argument("protofile")
@click.option("-i", "--include", multiple=True, help="Include path.")
@click.option("--mod", help="Protobuf api module name.")
@click.option("--msgcls", default='Config', help="Protobuf top message class name.")
@click.option("--yamlfile", required=True, help="YAML file with data.")
@click.option("--out", required=True, help="Serialized output file.")
@click.pass_context
def write(ctx, include, protofile, mod, msgcls, yamlfile, out):
    """Writes configuration binary from config proto file.
    """
    logger.debug(f"include={include}")

    if isinstance(include, tuple):
        include = list(include)
    else:
        include = [include]

    logger.info(f"Building api for {osp.basename(protofile)}")
    config_build(protofile, include)

    with open(yamlfile, 'r') as f:
        data = yaml.safe_load(f)
        logger.info(f"data={data}")

    config_write(mod, msgcls, data, out)


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
