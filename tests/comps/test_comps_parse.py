# -*- coding: utf-8 -*-

import os

from pubtools.pulplib._impl.comps import units_for_xml


def test_can_parse_units(data_path):
    """units_for_xml parses typical comps.xml data correctly."""

    xml_path = os.path.join(data_path, "sample-comps.xml")

    with open(xml_path, "rb") as f:
        units = units_for_xml(f)

    # Simply compare the returned value against expected.
    # Note, we are comparing elements one by one here to make it a bit
    # easier to deal with failures (failure message will be quite large
    # if entire list is compared at once).

    assert len(units) == 7

    assert units[0] == {
        "_content_type_id": "package_group",
        "conditional_package_names": [["blender", "something-required-by-blender"]],
        "default": False,
        "default_package_names": ["admesh"],
        "description": "3D printing software",
        "id": "3d-printing",
        "name": "3D Printing",
        "translated_description": {
            "af": "3D-druksagteware",
            "bg": "Софтуер за 3D печатане",
        },
        "translated_name": {"af": "3D-drukwerk", "bg": "3D Печатане"},
        "user_visible": True,
    }

    assert units[1] == {
        "_content_type_id": "package_group",
        "id": "admin-tools",
        "name": "Administration Tools",
        "translated_name": {"af": "Administrasienutsgoed", "am": "የአስተዳደሩ መሣሪያዎች"},
        "description": "This group is a collection of graphical administration tools for the system, such as for managing user accounts and configuring system hardware.",
        "translated_description": {
            "sr": "Ова група је скуп графичких системских административних алатки, нпр. за управљање корисничким налозима и подешавање хардвера у систему.",
            "sr@Latn": "Ova grupa je skup grafičkih sistemskih administrativnih alatki, npr. za upravljanje korisničkim nalozima i podešavanje hardvera u sistemu.",
        },
        "default": False,
        "user_visible": True,
        "mandatory_package_names": ["abrt-desktop", "gnome-disk-utility"],
    }

    assert units[2] == {
        "_content_type_id": "package_category",
        "id": "kde-desktop-environment",
        "name": "KDE Desktop",
        "translated_name": {"af": "KDE-werkskerm", "as": "KDE ডেস্কটপ"},
        "description": "The KDE SC includes the KDE Plasma Desktop, a highly-configurable graphical user interface which includes a panel, desktop, system icons and desktop widgets, and many powerful KDE applications.",
        "translated_description": {
            "bn_IN": "KDE SC-র মধ্যে রয়েছে KDE Plasma ডেস্কটপ। অতিমাত্রায় কনফিগার করার যোগ্য এই ইউজার ইন্টারফেসের মধ্যে রয়েছে একটি প্যানেল, ডেস্কটপ, সিস্টেমের বিভিন্ন আইকন ও ডেস্কটপ উইজেট ও বিভিন্ন উন্নত ক্ষমতাবিশিষ্ট KDE-র অন্যান্য অনেকগুলি অ্যাপ্লিকেশন।",
            "zh_TW": "KDE SC 所包含的 KDE Plasma 桌面是個功能強大的圖形使用者介面，它含有面板、桌面、系統圖示與桌面元件，以及許多強大的 KDE 應用軟體。",
        },
        "display_order": 10,
        "packagegroupids": ["kde-office", "kde-telepathy"],
    }

    assert units[3] == {
        "_content_type_id": "package_category",
        "id": "xfce-desktop-environment",
        "name": "Xfce Desktop",
        "translated_name": {"uk": "Графічне середовище Xfce", "zh_CN": "Xfce 桌面环境"},
        "description": "A lightweight desktop environment that works well on low end machines.",
        "translated_description": {
            "as": "এটা লঘুভাৰৰ ডেষ্কট'প পৰিবেশ যি নিম্ন বিন্যাসৰ যন্ত্ৰত ভালকৈ কাম কৰি ।",
            "ast": "Un entornu d'escritoriu llixeru que furrula bien en máquines pequeñes.",
        },
        "display_order": 15,
        "packagegroupids": ["xfce-apps", "xfce-desktop"],
    }

    assert units[4] == {
        "_content_type_id": "package_environment",
        "id": "basic-desktop-environment",
        "name": "Basic Desktop",
        "translated_name": {
            "af": "Basiese werkskerm",
            "bg": "Основен работен плот",
            "ca": "Escriptori bàsic",
        },
        "description": "X Window System with a choice of window manager.",
        "translated_description": {
            "af": "X Window-stelsel met ’n keuse van vensterbestuurder.",
            "bg": "X Window система с избор на мениджър на прозорци.",
        },
        "display_order": None,
        "group_ids": ["networkmanager-submodules", "standard"],
        "options": [{"default": True, "group": "xmonad"}, {"group": "xmonad-mate"}],
    }

    assert units[5] == {
        "_content_type_id": "package_environment",
        "id": "cinnamon-desktop-environment",
        "name": "Cinnamon Desktop",
        "translated_name": {"en_GB": "Cinnamon Desktop", "fr": "Bureau Cinnamon"},
        "translated_description": {
            "ca": "Cinnamon proporciona un escriptori amb un disseny tradicional, funcionalitats avançades, facilitat d'ús, potent i flexible.",
            "es": "Cinnamon proporciona un entorno de escritorio tradicional, con características avanzadas, fácil de usar, potente y flexible.",
        },
        "display_order": 22,
        "group_ids": ["input-methods", "multimedia"],
        "options": [{"group": "libreoffice"}],
    }

    assert units[6] == {
        "_content_type_id": "package_langpacks",
        "matches": [
            {"install": "stardict-dic-%s", "name": "stardict"},
            {"install": "tagainijisho-dic-%s", "name": "tagainijisho-common"},
            {"install": "tesseract-langpack-%s", "name": "tesseract"},
            {"install": "tkgate-%s", "name": "tkgate"},
        ],
    }
