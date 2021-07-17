$XONSH_COLOR_STYLE = "default"  # Until the "egnor" style is defined.

xontrib load apt_tabcomplete direnv kitty linuxbrew

$SHELL_TYPE = "prompt_toolkit"
$XONSH_SHOW_TRACEBACK = False
$VI_MODE = True

$PATH.add(str(p"~/.poetry/bin"), front=True, replace=True)
$PATH.add(str(p"~/.local/bin"), front=True, replace=True)
$PATH.add(str(p"~/npm/bin"), front=True, replace=True)
$PATH.add(str(p"~/go/bin"), front=True, replace=True)

aliases["ls"] = "ls -A -F --color=auto"

source ~/.config/xonsh/my_colors.xsh
source ~/.config/xonsh/my_prompt.xsh
