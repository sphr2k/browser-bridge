class BrowserBridge < Formula
  desc "Open macOS browser and Finder from a Lima Linux guest over Unix sockets"
  homepage "https://github.com/sphr2k/browser-bridge"
  url "https://raw.githubusercontent.com/sphr2k/browser-bridge/v0.1.0/bin/browser-bridge", using: :nounzip
  version "0.1.0"
  sha256 "fecb51d79e34dcc04264c799eaa3ce61d9194d6974b9c1e90be896f95a14bda0"
  license "MIT"

  depends_on "python@3.14"

  def install
    python = Formula["python@3.14"].opt_bin/"python3.14"
    inreplace "browser-bridge", "#!/usr/bin/env python3", "#!#{python}"
    bin.install "browser-bridge"
    chmod 0755, bin/"browser-bridge"
  end

  service do
    run macos: [opt_bin/"browser-bridge", "serve"]
    keep_alive true
    log_path var/"log/browser-bridge.log"
    error_log_path var/"log/browser-bridge.err.log"
  end

  test do
    assert_match "browser-bridge 0.1.0", shell_output("#{bin}/browser-bridge --version")
  end
end
