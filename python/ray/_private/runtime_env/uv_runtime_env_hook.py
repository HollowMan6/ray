import argparse
import copy
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil


def _check_working_dir_files(
    uv_run_args: List[str], runtime_env: Dict[str, Any]
) -> None:
    """
    Check that the files required by uv are local to the working_dir. This catches
    the most common cases of how things are different in Ray, i.e. not the whole file
    system will be available on the workers, only the working_dir.

    The function won't return anything, it just raises a RuntimeError if there is an error.
    """
    # First parse the arguments we need to check
    uv_run_parser = argparse.ArgumentParser()
    uv_run_parser.add_argument("--with-requirements", nargs="?")
    uv_run_parser.add_argument("--project", nargs="?")
    uv_run_parser.add_argument("--no-project", action="store_true")
    known_args, _ = uv_run_parser.parse_known_args(uv_run_args)

    working_dir = Path(runtime_env["working_dir"]).resolve()

    # Check if the requirements.txt file is in the working_dir
    if known_args.with_requirements and not Path(
        known_args.with_requirements
    ).resolve().is_relative_to(working_dir):
        raise RuntimeError(
            f"You specified --with-requirements={known_args.with_requirements} but "
            f"the requirements file is not in the working_dir {runtime_env['working_dir']}, "
            "so the workers will not have access to the file. Make sure "
            "the requirements file is in the working directory. "
            "You can do so by specifying --directory in 'uv run', by changing the current "
            "working directory before running 'uv run', or by using the 'working_dir' "
            "parameter of the runtime_environment."
        )

    # Check if the pyproject.toml file is in the working_dir
    pyproject = None
    if known_args.no_project:
        pyproject = None
    elif known_args.project:
        pyproject = Path(known_args.project)
    else:
        # Walk up the directory tree until pyproject.toml is found
        current_path = Path.cwd().resolve()
        while current_path != current_path.parent:
            if (current_path / "pyproject.toml").exists():
                pyproject = Path(current_path / "pyproject.toml")
                break
            current_path = current_path.parent

    if pyproject and not pyproject.resolve().is_relative_to(working_dir):
        raise RuntimeError(
            f"Your {pyproject.resolve()} is not in the working_dir {runtime_env['working_dir']}, "
            "so the workers will not have access to the file. Make sure "
            "the pyproject.toml file is in the working directory. "
            "You can do so by specifying --directory in 'uv run', by changing the current "
            "working directory before running 'uv run', or by using the 'working_dir' "
            "parameter of the runtime_environment."
        )


def _get_uv_run_cmdline() -> Optional[List[str]]:
    """
    Return the command line of the first ancestor process that was run with
    "uv run" and None if there is no such ancestor.

    uv spawns the python process as a child process, so we first check the
    parent process command line. We also check our parent's parents since
    the Ray driver might be run as a subprocess of the 'uv run' process.
    """
    parents = psutil.Process().parents()
    for parent in parents:
        try:
            cmdline = parent.cmdline()
            if (
                len(cmdline) > 1
                and os.path.basename(cmdline[0]) == "uv"
                and cmdline[1] == "run"
            ):
                return cmdline
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            continue
    return None


def hook(runtime_env: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Hook that detects if the driver is run in 'uv run' and sets the runtime environment accordingly."""

    runtime_env = copy.deepcopy(runtime_env) or {}

    cmdline = _get_uv_run_cmdline()
    if not cmdline:
        # This means the driver was not run in a 'uv run' environment -- in this case
        # we leave the runtime environment unchanged
        return runtime_env

    # First check that the "uv" and "pip" runtime environments are not used.
    if "uv" in runtime_env or "pip" in runtime_env:
        raise RuntimeError(
            "You are using the 'pip' or 'uv' runtime environments together with "
            "'uv run'. These are not compatible since 'uv run' will run the workers "
            "in an isolated environment -- please add the 'pip' or 'uv' dependencies to your "
            "'uv run' environment e.g. by including them in your pyproject.toml."
        )

    # Extract the arguments of 'uv run' that are not arguments of the script.
    # First we get the arguments of this script (without the executable):
    script_args = psutil.Process().cmdline()[1:]
    # Then, we remove those arguments from the parent process commandline:
    uv_run_args = cmdline[: len(cmdline) - len(script_args)]

    # Remove the "--directory" argument since it has already been taken into
    # account when setting the current working directory of the current process
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", nargs="?")
    _, remaining_uv_run_args = parser.parse_known_args(uv_run_args)

    runtime_env["py_executable"] = " ".join(remaining_uv_run_args)

    # If the user specified a working_dir, we always honor it, otherwise
    # use the same working_dir that uv run would use
    if "working_dir" not in runtime_env:
        runtime_env["working_dir"] = os.getcwd()
        _check_working_dir_files(uv_run_args, runtime_env)

    return runtime_env


# This __main__ is used for unit testing if the runtime_env_hook picks up the
# right settings.
if __name__ == "__main__":
    import json

    test_parser = argparse.ArgumentParser()
    test_parser.add_argument("runtime_env")
    args = test_parser.parse_args()

    # If the env variable is set, add one more level of subprocess indirection
    if os.environ.get("RAY_TEST_UV_ADD_SUBPROCESS_INDIRECTION") == "1":
        import subprocess

        env = os.environ.copy()
        env.pop("RAY_TEST_UV_ADD_SUBPROCESS_INDIRECTION")
        subprocess.check_call([sys.executable] + sys.argv, env=env)
        sys.exit(0)

    # We purposefully modify sys.argv here to make sure the hook is robust
    # against such modification.
    sys.argv.pop(1)
    runtime_env = json.loads(args.runtime_env)
    print(json.dumps(hook(runtime_env)))
