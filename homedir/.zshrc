bindkey -v
setopt GLOB_DOTS
ls() { /bin/ls -A -F "$@" }

typeset -TU PATH path
path=(~/.poetry/bin ~/.local/bin ~/npm/bin ~/go/bin $path)

autoload compinit
compinit -C -d ~/.zcompdump-$ZSH_VERSION

PROMPT='%# '
RPROMPT=' %(?..%? )%~ %B%m%b'

test -n $commands[direnv] && eval "$(direnv hook zsh)"
test -x $commands[kitty] && eval "$(kitty + complete setup zsh)"
test -x ~/.linuxbrew/bin/brew && eval "$(~/.linuxbrew/bin/brew shellenv)"
test -e ~/.nix-profile/etc/profile.d/nix.sh && . ~/.nix-profile/etc/profile.d/nix.sh
