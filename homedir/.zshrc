autoload compinit
compinit -C -d ~/.zcompdump-$ZSH_VERSION

# zsh preferences
bindkey -v
setopt GLOB_DOTS
PROMPT='%# '
RPROMPT=' %(?..%? )%~ %B%m%b'
[[ "egnor" != "$USERNAME" ]] && PROMPT="%B$USERNAME%b $PROMPT"

# Set terminal type 
export TERMINFO_DIRS=/usr/share/terminfo:/etc/terminfo:/lib/terminfo
if [[ -z "$TERM_FALLBACK" ]]; then
  for TERM_FALLBACK in ${(s:,:)LC_TERM_FALLBACK}; do
    if infocmp "$TERM_FALLBACK" &> /dev/null; then
      export TERM="$TERM_FALLBACK"
      export TERM_FALLBACK
      break
    fi
  done
fi

# Use last fallback for outgoing ssh
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
