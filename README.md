# browser-bridge

Open URLs in the macOS default browser and open or reveal host files in Finder from a Lima Linux guest, using a forwarded Unix socket.

Pure Python standard library. No TCP ports, additional Python packages, or guest-side service.

## Installation: mise only

Requires mise 2026.11+ and Python 3.10+.

Merge the following TOML into your global ~/.config/mise/config.toml on **both** the macOS host and Linux guest. The macOS-only bootstrap section is ignored on Linux. The same configuration is provided in [mise.toml](mise.toml).

~~~toml
[tools."http:browser-bridge"]
version = "0.2.0"
url = "https://raw.githubusercontent.com/sphr2k/browser-bridge/v{{ version }}/bin/browser-bridge"
bin = "browser-bridge"
checksum = "sha256:1d104ae3cde66b697316fe97652f84337671ee285b3290985d7b4d2539030fb5"

[bootstrap.macos.launchd.agents.browser-bridge]
program = "~/.local/bin/mise"
args = ["exec", "--", "browser-bridge", "serve"]
run_at_load = true
keep_alive = true
~~~

The launch agent's program path is for the official [mise.run installer](https://mise.jdx.dev/installing-mise.html), which installs mise at ~/.local/bin/mise. If you installed mise elsewhere, replace that with the absolute, stable path to your mise executable. Do not use a dynamic shell shim. Do not overwrite your global config; merge the sections into it.

On **both** macOS and Linux, install the tool:

~~~sh
mise install
mise exec -- browser-bridge --version
~~~

On the **macOS host** register the launchd agent (as your normal user; no sudo):

~~~sh
mise bootstrap macos launchd-agents apply --dry-run
mise bootstrap macos launchd-agents apply --yes
mise bootstrap macos launchd-agents status
~~~

Mise creates ~/Library/LaunchAgents/dev.mise.browser-bridge.plist, starts the service at login and automatically restarts it on exit. Remove with mise bootstrap services remove browser-bridge.

Install with mise install *before* applying the LaunchAgent. The full mise bootstrap normally processes macOS LaunchAgents before installing tools, so these two explicit steps ensure the executable is present.

### Lima VM

Merge into the existing portForwards list in your Lima VM configuration (limactl edit <vm-name>):

~~~yaml
portForwards:
  - guestSocket: "{{.Home}}/.lima-browser-bridge.sock"
    hostSocket: "{{.Home}}/.lima/browser-bridge.sock"
    reverse: true
~~~

Restart the VM to apply. The macOS listener is ~/.lima/browser-bridge.sock (0600); the Linux client uses ~/.lima-browser-bridge.sock. reverse: true forwards from Linux into the macOS socket.

### Linux: BROWSER and xdg-open

After installing with mise inside the guest:

~~~sh
export BROWSER="$(mise which browser-bridge)"
browser-bridge open https://github.com/login/device
~~~

To support xdg-open:

~~~sh
mkdir -p ~/.local/bin
ln -s "$(mise which browser-bridge)" ~/.local/bin/xdg-open
export PATH="$HOME/.local/bin:$PATH"
xdg-open https://github.com
~~~

Only create the symlink if there is no existing ~/.local/bin/xdg-open. If you upgrade the mise tool to a new version, update the version-specific symlink or use a wrapper.

## Browser and Finder

~~~sh
browser-bridge open https://github.com
browser-bridge open /Users/you/projects
browser-bridge reveal /Users/you/projects/notes.txt
browser-bridge open file:///Users/you/projects
xdg-open /Users/you/projects
~~~

File paths are interpreted on the **macOS host**, not on Linux. A Linux-only path (for example /home/user/repo) is not automatically visible to Finder. Use a host-visible path or an equivalent Lima mount. open launches files in their default macOS app (folders in Finder); reveal selects files in Finder.

## CLI

~~~text
browser-bridge open URL_OR_HOST_PATH [--socket GUEST_SOCKET]
browser-bridge reveal HOST_PATH [--socket GUEST_SOCKET]
browser-bridge serve [--socket HOST_SOCKET]  # macOS only
browser-bridge URL_OR_HOST_PATH             # BROWSER / xdg-open compatible
browser-bridge --version
~~~

## Security

No network listener. The service runs as the macOS user with a private 0600 Unix socket, accepts only open and reveal with HTTP(S) URLs or absolute host paths, and invokes /usr/bin/open without a shell. Any trusted guest that can use the forwarded socket can request that macOS open local documents or applications; use only with trusted guests. No file transfers or arbitrary shell execution.

## Development

~~~sh
python3 -m unittest discover -s tests -v
~~~

MIT license. Mise-only from v0.2.0 onward; the previous v0.1.0 Homebrew distribution is not maintained.
