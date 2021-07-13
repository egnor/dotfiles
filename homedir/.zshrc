ls() { /bin/ls -A -F "$@" }

bindkey -v
typeset -U FPATH LD_LIBRARY_PATH PATH

fpath=(~/.functions $fpath)
autoload compinit
compinit -C -d ~/.zcompdump-$ZSH_VERSION

setopt GLOB_DOTS
export PROMPT='%# '
export RPROMPT=' %(?..%? )%~ %B%m%b'

typeset -T LD_LIBRARY_PATH ld_library_path
ld_library_path=(~/.local/lib $ld_library_path)
export LD_LIBRARY_PATH

path=(~/.poetry/bin ~/.local/bin ~/npm/bin ~/go/bin $path)

test -n $commands[direnv] && eval "$(direnv hook zsh)"
test -x ~/.linuxbrew/bin/brew && eval "$(~/.linuxbrew/bin/brew shellenv)"
