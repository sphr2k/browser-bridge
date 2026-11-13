# browser-bridge

Open URLs in the **macOS default browser**, and host files/directories in **Finder or their default macOS app**, from a **Lima Linux guest**.

A single Python standard-library script. No TCP listener, browser extension, extra CLI daemon on Linux, or third-party Python packages.

## Install on macOS and Linux

Homebrew tap (explicit URL because the repository is named browser-bridge, without the homebrew- prefix):

~~~sh
brew tap sphr2k/browser-bridge https://github.com/sphr2k/browser-bridge
brew install sphr2k/browser-bridge/browser-bridge
~~~

### macOS host: launchd

Start as a user service (do **not** use sudo):

~~~sh
brew services start sphr2k/browser-bridge/browser-bridge
brew services list
~~~

The service listens at ~/.lima/browser-bridge.sock (mode 0600). Homebrew installs and manages a launchd agent that starts at login and restarts after failures.

Stop with:

~~~sh
brew services stop sphr2k/browser-bridge/browser-bridge
~~~

### Lima: forward Unix socket

Merge this into your Lima VM configuration (limactl edit <vm-name>):

~~~yaml
portForwards:
  - guestSocket: "{{.Home}}/.lima-browser-bridge.sock"
    hostSocket: "{{.Home}}/.lima/browser-bridge.sock"
    reverse: true
~~~

Restart the VM after changing portForwards. These are separate host and guest socket paths. With reverse: true, Lima forwards requests from the guest into the macOS listener. If a portForwards array exists, add only this entry rather than overwriting other rules.

### Linux guest: client

Install the same formula, then:

~~~sh
browser-bridge open https://github.com/login/device
browser-bridge https://example.org
~~~

For CLI tools that use BROWSER or xdg-open, optionally configure:

~~~sh
mkdir -p ~/.local/bin
ln -s "$(command -v browser-bridge)" ~/.local/bin/xdg-open
export PATH="$HOME/.local/bin:$PATH"
export BROWSER="$(command -v browser-bridge)"
xdg-open https://github.com
~~~

Put the exports in your shell startup configuration to make them persistent. Do not overwrite an existing ~/.local/bin/xdg-open without checking it. For tools that respect BROWSER, only the BROWSER export is needed.

## Open Finder directories and reveal files

~~~sh
browser-bridge open /Users/you/projects
browser-bridge reveal /Users/you/projects/notes.txt
browser-bridge open file:///Users/you/projects
xdg-open /Users/you/projects
~~~

Paths refer to the **macOS host filesystem**, not necessarily the Linux guest filesystem. A Linux-only path such as /home/user/project cannot be opened in Finder. Supply a host path or use a Lima-mounted host directory whose paths agree. The open command uses the OS default application (Finder for directories); reveal selects a file in Finder without opening it.

## CLI reference

~~~text
browser-bridge open URL_OR_HOST_PATH [--socket GUEST_SOCKET]
browser-bridge reveal HOST_PATH [--socket GUEST_SOCKET]
browser-bridge serve [--socket HOST_SOCKET]     # macOS only
browser-bridge URL_OR_HOST_PATH                 # compatible with BROWSER and xdg-open
browser-bridge --version
~~~

Default socket locations:

| Machine | Socket |
|---------|--------|
| macOS host | ~/.lima/browser-bridge.sock |
| Lima guest | ~/.lima-browser-bridge.sock |

## Security

- Only HTTP(S) URLs and absolute paths are accepted. The host accepts the JSON-line actions open and reveal, and never executes a shell command.
- The host listener is a 0600 Unix socket; no network TCP port is opened.
- Use the service without sudo on trusted Lima guests only. A connected guest can ask the host to open a local document or application, including files with potentially unsafe associations.
- The tool does not transfer files or grant access to files that are not already visible on the macOS host.

## Development

~~~sh
python3 -m unittest discover -s tests -v
~~~

Python 3.10+; Homebrew uses python@3.14 on both macOS and Linux. MIT license.
