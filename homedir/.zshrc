autoload compinit
compinit -C -d ~/.zcompdump-$ZSH_VERSION

bindkey -v
setopt GLOB_DOTS
PROMPT='%# '
RPROMPT=' %(?..%? )%~ %B%m%b'

typeset -TU PATH path
path=(~/.poetry/bin ~/.local/bin ~/npm/bin ~/go/bin $path)

export TERMINFO_DIRS=/usr/share/terminfo:/etc/terminfo:/lib/terminfo

test -n "$commands[kitty]" && eval "$(kitty + complete setup zsh)"
test -x ~/.linuxbrew/bin/brew && eval "$(~/.linuxbrew/bin/brew shellenv)"
test -x /home/linuxbrew/.linuxbrew/bin/brew && eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

ls() { /bin/ls -A -F "$@" }

eval "$(direnv hook zsh)"
