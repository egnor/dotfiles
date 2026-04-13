autoload compinit
compinit -C -d ~/.zcompdump-$ZSH_VERSION

bindkey -v
setopt GLOB_DOTS
PROMPT='%# '
RPROMPT=' %(?..%? )%~ %B%m%b'
[[ "egnor" != "$USERNAME" ]] && PROMPT="%B$USERNAME%b $PROMPT"

export TERMINFO_DIRS=/usr/share/terminfo:/etc/terminfo:/lib/terminfo

# Upgrade TERM from LC_TERM if ssh forwarded a value the local terminfo supports
if [[ -n "$LC_TERM" && "$LC_TERM" != "$TERM" ]] && infocmp "$LC_TERM" &>/dev/null; then
  export TERM=$LC_TERM
fi
unset LC_TERM

typeset -TU PATH path
path=(~/.local/bin ~/.meteor $path)
path=(/var/lib/flatpak/exports/bin ~/.local/share/flatpak/exports/bin $path)

test -x ~/.linuxbrew/bin/brew && eval "$(~/.linuxbrew/bin/brew shellenv)"
test -x /home/linuxbrew/.linuxbrew/bin/brew && eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
(( $+commands[mise] )) && eval "$(mise activate --status zsh)"
(( $+commands[fzf] )) && eval "$(fzf --zsh)"
(( $+commands[nvim] )) && vi() { nvim "$@" }

ls() { command ls -A -F "$@" }
mr() { mise run "$@" }
R() { command R --no-save "$@" }
ssh() { LC_TERM="$TERM" TERM=xterm-256color command ssh "$@" }
export PATH=/home/egnor/.meteor:$PATH
