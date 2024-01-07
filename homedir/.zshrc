autoload compinit
compinit -C -d ~/.zcompdump-$ZSH_VERSION

bindkey -v
setopt GLOB_DOTS
PROMPT='%# '
RPROMPT=' %(?..%? )%~ %B%m%b'

export TERMINFO_DIRS=/usr/share/terminfo:/etc/terminfo:/lib/terminfo

typeset -TU PATH path
path=(~/.local/bin ~/.meteor $path)
path=(/var/lib/flatpak/exports/bin ~/.local/share/flatpak/exports/bin $path)

test -x ~/.linuxbrew/bin/brew && eval "$(~/.linuxbrew/bin/brew shellenv)"
test -x /home/linuxbrew/.linuxbrew/bin/brew && eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
(( $+commands[direnv] )) && eval "$(direnv hook zsh)"
(( $+commands[mise] )) && eval "$(mise activate zsh)"

ls() { command ls -A -F "$@" }
R() { command R --no-save "$@" }
