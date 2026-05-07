autoload compinit
compinit -C -d ~/.zcompdump-$ZSH_VERSION

# zsh preferences
bindkey -v
setopt GLOB_DOTS
PROMPT='%# '
RPROMPT=' %(?..%? )%~ %B%m%b'
[[ "egnor" != "$USERNAME" ]] && PROMPT="%B$USERNAME%b $PROMPT"

if [[ -z "$TERM_FOUND" ]]; then
  TERMINFO_DIRS=/usr/share/terminfo:/etc/terminfo:/lib/terminfo
  for TERM_SUDO in ${(s:,:)LC_TERM_FALLBACK} ""; do
    infocmp "$TERM_SUDO" &>/dev/null && break
  done

  TERMINFO_DIRS=$HOME/.local/kitty.app/share/terminfo:$TERMINFO_DIRS
  for TERM_FOUND in ${(s:,:)LC_TERM_FALLBACK} ""; do
    infocmp "$TERM_FOUND" &> /dev/null && break
  done

  export TERM="${TERM_FOUND:-$TERM}" TERMINFO_DIRS TERM_FOUND TERM_SUDO
fi

# Use systemwide fallback for sudo, last fallback for outgoing ssh
sudo() { TERM="${TERM_SUDO:-$TERM}" command sudo "$@" }
ssh() { TERM="${${LC_TERM_FALLBACK##*,}:-${TERM}}" command ssh "$@" }

# typeset -TU PATH path
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
export PATH=/home/egnor/.meteor:$PATH
