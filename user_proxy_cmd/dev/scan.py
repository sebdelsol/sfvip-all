from dev.scan import do_scan
from user_proxy_cmd import cmd_build_config

if __name__ == "__main__":
    do_scan(cmd_build_config.Build, cmd_build_config.Environments, cmd_build_config.Templates)
