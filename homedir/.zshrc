autoload compinit
compinit -C -d ~/.zcompdump-$ZSH_VERSION

# zsh preferences
bindkey -v
setopt GLOB_DOTS
PROMPT='%# '
RPROMPT=' %(?..%? )%~ %B%m%b'
[[ "egnor" != "$USERNAME" ]] && PROMPT="%B$USERNAME%b $PROMPT"

if [[ -z "$TERM_SET" ]]; then
  TERMINFO_DIRS=/usr/share/terminfo:/etc/terminfo:/lib/terminfo
  for term_sudo in ${(s:,:)LC_TERM_FALLBACK} ""; do
    infocmp "$term_sudo" &>/dev/null && break
  done

  TERMINFO_DIRS=$HOME/.local/kitty.app/share/terminfo:$TERMINFO_DIRS
  for term_found in ${(s:,:)LC_TERM_FALLBACK} ""; do
    infocmp "$term_found" &> /dev/null && break
  done

  export TERM="${term_found:-$TERM}" TERMINFO_DIRS TERM_SET=1
fi

# Use systemwide fallback for sudo, last fallback for outgoing ssh
sudo() { TERM="${term_sudo:-$TERM}" command sudo "$@" }
ssh() { TERM="${${LC_TERM_FALLBACK##*,}:-${TERM}}" command ssh "$@" }

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
export PATH=/home/egnor/.meteor:$PATH
