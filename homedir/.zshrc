autoload compinit
compinit -C -d ~/.zcompdump-$ZSH_VERSION

bindkey -v
setopt GLOB_DOTS
PROMPT='%# '
RPROMPT=' %(?..%? )%~ %B%m%b'

typeset -TU PATH path
path=(~/.poetry/bin ~/.local/bin ~/npm/bin ~/go/bin $path)

export TERMINFO_DIRS=/usr/share/terminfo:/etc/terminfo:/lib/terminfo

test -n "$commands[direnv]" && eval "$(direnv hook zsh)"
test -n "$commands[kitty]" && eval "$(kitty + complete setup zsh)"
test -x ~/.linuxbrew/bin/brew && eval "$(~/.linuxbrew/bin/brew shellenv)"
test -e ~/.nix-profile/etc/profile.d/nix.sh && . ~/.nix-profile/etc/profile.d/nix.sh

ls() { /bin/ls -A -F "$@" }
