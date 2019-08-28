# -*- coding: utf-8 -*-"

kernel_site = "https://git.kernel.org/"
upstream_repo = kernel_site + "pub/scm/linux/kernel/git/torvalds/linux"
stable_repo = kernel_site + "pub/scm/linux/kernel/git/stable/linux-stable"

chromium_site = "https://chromium.googlesource.com/"
chromeos_repo = chromium_site + "chromiumos/third_party/kernel"

stable_branches = ('4.4', '4.9', '4.14', '4.19', '5.2')
stable_pattern = 'linux-%s.y'

chromeos_branches = ('4.4', '4.14', '4.19')
chromeos_pattern = 'chromeos-%s'

chromeos_path = "linux-chrome"
stable_path = "linux-stable"
upstream_path = "linux-upstream"
