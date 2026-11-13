# browser-bridge

Open URLs in the **macOS default browser** and open or reveal host files in **Finder** from a **Lima Linux guest**, using a forwarded Unix socket.

Pure Python standard library. No TCP ports, additional Python packages, or guest-side service.

## Install via mise (macOS and Linux)

Requires mise 2026.11+ and Python 3.10+.

**Run the same command on both the macOS host and the Lima Linux guest:**

~~~sh
mise use -g \
  --tool-option url=https://raw.githubusercontent.com/sphr2k/browser-bridge/v0.2.0/bin/browser-bridge \
  --tool-option bin=browser-bridge \
  --tool-option checksum=sha256:1d104ae3cde66b697316fe97652f84337671ee285b3290985d7b4d2539030fb5 \
  http:browser-bridge@0.2.0

mise exec -- browser-bridge --version
~~~

This **installs and pins the tool globally** in your existing mise config. No clone, Homebrew tap or manual copying is needed. The HTTP backend installs the published single-file Python executable, verified by SHA-256.

If you prefer declarative TOML, the same pinned definition is in [mise.toml](mise.toml). Merge the tool section into your global ~/.config/mise/config.toml and run mise install. Do not replace the rest of your existing config.

## macOS host: launchd managed by mise

The host needs a background listener. Add the following **only on macOS** to your global ~/.config/mise/config.toml (already included as a reusable example in [mise.toml](mise.toml)):

~~~toml
[bootstrap.macos.launchd.agents.browser-bridge]
program = "~/.local/bin/mise"
args = ["exec", "--", "browser-bridge", "serve"]
run_at_load = true
keep_alive = true
~~~

Change program to the stable absolute path from command -v mise if yours is not ~/.local/bin/mise. Avoid a dynamically generated shell shim. Then apply the LaunchAgent as your normal macOS user:

~~~sh
mise bootstrap macos launchd-agents apply --dry-run
mise bootstrap macos launchd-agents apply --yes
mise bootstrap macos launchd-agents status
~~~

Mise creates ~/Library/LaunchAgents/dev.mise.browser-bridge.plist. The listener starts at login and restarts when necessary. The socket is ~/.lima/browser-bridge.sock (mode 0600). Install with mise use -g first; launchd should not be started before the tool is present.

## Lima: connect the guest to the macOS socket

On macOS, add the following to your existing Lima instance config via limactl edit <instance-name>. If portForwards already exists, append the entry instead of replacing the array:

~~~yaml
portForwards:
  - guestSocket: "{{.Home}}/.lima-browser-bridge.sock"
    hostSocket: "{{.Home}}/.lima/browser-bridge.sock"
    reverse: true
~~~

Restart the VM after changing its config. reverse: true forwards a guest Unix socket into the macOS host socket; there is no TCP listener and no additional proxy required.

## Lima Linux guest: optional one-command mise bootstrap

After configuring the Lima socket forwarding above, **run inside the Linux guest**:

~~~sh
mise bootstrap \
  --from https://github.com/sphr2k/browser-bridge.git \
  -E lima --only tools,dotfiles,task --yes
~~~

This reads the optional [mise.lima.toml](mise.lima.toml) module and performs all Linux client setup with mise:

- Installs and pins browser-bridge globally via mise use -g, including its SHA-256 checksum.
- Sets the global mise environment variable BROWSER=browser-bridge.
- Deploys an executable ~/.local/bin/xdg-open wrapper through mise dotfiles that calls mise exec -- browser-bridge.
- Preserves an existing ~/.local/bin/xdg-open instead of replacing it (create_if_missing = true).

It intentionally **does not start a Linux service**. Lima supplies the guest socket, and the macOS launchd service handles each request.

Check that ~/.local/bin occurs before /usr/bin on PATH:

~~~sh
mise exec -- browser-bridge --version
command -v xdg-open
xdg-open https://github.com/login/device
~~~

The desired xdg-open path is ~/.local/bin/xdg-open. If it is not on PATH, add ~/.local/bin to your shell startup config. BROWSER is exported by an activated mise shell (or when launching programs via mise exec); otherwise export BROWSER=browser-bridge yourself.

**Alternatively, install without the optional bootstrap:** use the mise use -g command from the first section and follow the manual setup below.

## Lima Linux guest: manual setup (alternative)

After running the same mise use -g installation command from the first section **inside the guest**, set the browser environment for shells managed by mise:

~~~sh
mise set -g BROWSER=browser-bridge
mise exec -- browser-bridge open https://github.com/login/device
~~~

With mise shell activation, the BROWSER value becomes available to programs started from your shell. If you are not using shell activation, run tools via mise exec or export BROWSER=browser-bridge in your shell profile.

Some programs ignore BROWSER and invoke xdg-open. To cover those, create a simple wrapper that continues to work across browser-bridge version upgrades:

~~~sh
mkdir -p ~/.local/bin
if [ -e ~/.local/bin/xdg-open ] || [ -L ~/.local/bin/xdg-open ]; then
  echo "xdg-open already exists; inspect it before replacing" >&2
else
  cat > ~/.local/bin/xdg-open <<'SH'
#!/bin/sh
exec mise exec -- browser-bridge "$@"
SH
  chmod +x ~/.local/bin/xdg-open
fi
export PATH="$HOME/.local/bin:$PATH"
xdg-open https://github.com/login/device
~~~

Put ~/.local/bin on PATH persistently in your Linux shell profile. The wrapper requires the mise executable on PATH, which is normally already true in a mise-managed shell.

**No guest daemon, systemd unit, launchd configuration, or socket server is necessary on Linux.** The CLI connects to ~/.lima-browser-bridge.sock, which is provided by Lima's reverse forwarding. Use browser-bridge open https://example.org --socket /custom/path if you configure a different guest socket.

## Browser and Finder

~~~sh
browser-bridge open https://github.com
browser-bridge open /Users/you/projects
browser-bridge reveal /Users/you/projects/notes.txt
browser-bridge open file:///Users/you/projects
xdg-open /Users/you/projects
~~~

File paths are interpreted on the **macOS host**, not on Linux. A Linux-only path (for example /home/user/repo) cannot be opened in Finder unless it is also accessible on macOS under the provided path. open launches files in their default macOS app (directories in Finder); reveal selects them in Finder.

## CLI reference

~~~text
browser-bridge open URL_OR_HOST_PATH [--socket GUEST_SOCKET]
browser-bridge reveal HOST_PATH [--socket GUEST_SOCKET]
browser-bridge serve [--socket HOST_SOCKET]   # macOS only
browser-bridge URL_OR_HOST_PATH              # BROWSER / xdg-open compatible
browser-bridge --version
~~~

## Security

No network listener. The host service runs as the macOS user with a private 0600 Unix socket, accepts only open and reveal with HTTP(S) URLs or absolute host paths, and invokes /usr/bin/open without a shell. A trusted guest with access to the socket can still ask the host to open local files or applications; do not expose the socket to untrusted workloads. The tool does not transfer files.

## Development

~~~sh
python3 -m unittest discover -s tests -v
~~~

MIT license. Mise-only from v0.2.0 onward; the historical v0.1.0 Homebrew packaging is not maintained.
