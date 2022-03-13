# -*- coding: utf-8 -*-

from xml.parsers import expat

from six import StringIO


class BooleanStringIO(StringIO):
    """A StringIO which coerces the output value into a boolean."""

    def getvalue(self):
        # Note: StringIO in python2 is an old-style class, so no super().
        value = StringIO.getvalue(self).strip()
        if value.lower() in ("false", ""):
            return False
        return True


class IntegerStringIO(StringIO):
    """A StringIO which coerces the output value into an integer."""

    def getvalue(self):
        value = StringIO.getvalue(self).strip()
        if not value:
            return None
        return int(value)


def close_buffers(value):
    """Returns a copy of 'value' with all StringIO buffers replaced with the
    content of each buffer.

    This is used at the end of parsing, once we know that no more text data can
    arrive, to seal the output and convert into a serializable form.
    """

    if isinstance(value, list):
        return [close_buffers(elem) for elem in value]

    if isinstance(value, dict):
        out = {}
        for (key, elem) in value.items():
            out[key] = close_buffers(elem)
        return out

    if isinstance(value, StringIO):
        return value.getvalue()

    return value


class CompsParser(object):
    """A stateful parser for comps.xml data.

    This parser wraps xml.parsers.expat and installs handlers which are able to
    load XML elements into the form used by Pulp for the relevant unit types.
    """

    def __init__(self):
        self.raw_parser = expat.ParserCreate()

        # Current parse state. The output is ultimately returned from 'units'.
        self.units = []
        self.current_buf = StringIO()
        self.current_unit = {}
        self.current_path = []

        # Bind ourselves to expat.
        for name in dir(self):
            if name.endswith("Handler"):
                setattr(self.raw_parser, name, getattr(self, name))

    def parse(self, io):
        """Parse comps XML from io, a file-like object in binary mode.

        Returns parsed units in Pulp form (i.e. a list of dicts with each dict
        having the Pulp-specific attributes such as _content_type_id, ...)
        """
        self.units = []
        self.current_unit = {}
        self.current_path = []
        self.raw_parser.ParseFile(io)
        self.units = close_buffers(self.units)
        return self.units

    ########################## Shared handlers #########################
    # Handle some basic tags shared by multiple types such as:
    #
    #     <id>kde-desktop-environment</id>
    #     <name>KDE Desktop</name>
    #     <name xml:lang="af">KDE-werkskerm</name>
    #     <name xml:lang="as">KDE ডেস্কটপ</name>
    #     ...
    #     <description>The KDE SC includes ...</description>
    #     <description xml:lang="ar">الـ KDE SC يتضمن سطح...</description>

    def handle_text_elem(self, tag, attrs):
        if tag in ("name", "description") and attrs.get("xml:lang"):
            # Elem like this: <name xml:lang="af">3D-drukwerk</name>
            # Is parsed into: translated_name["af"] = "3D-drukwerk"
            tag = "translated_" + tag
            lang = attrs["xml:lang"]
            self.current_buf = StringIO()
            self.current_unit.setdefault(tag, {})[lang] = self.current_buf
            return True

        elif tag in ("id", "name", "description"):
            self.current_buf = StringIO()
            self.current_unit[tag] = self.current_buf
            return True

        return False

    def handle_display_order_tag(self, tag):
        if tag == "display_order":
            self.current_buf = IntegerStringIO()
            self.current_unit[tag] = self.current_buf
            return True
        return False

    ########################## Group ###################################
    #   <group>
    #     <id>3d-printing</id>
    #     <name>3D Printing</name>
    #     <name xml:lang="af">3D-drukwerk</name>
    #     <name xml:lang="bg">3D Печатане</name>
    #     ...
    #     <description>3D printing software</description>
    #     <description xml:lang="af">3D-druksagteware</description>
    #     <description xml:lang="bg">Софтуер за 3D печатане</description>
    #     ...
    #     <default>false</default>
    #     <uservisible>true</uservisible>
    #     <packagelist>
    #       <packagereq type="default">admesh</packagereq>
    #       <packagereq type="default">blender</packagereq>
    #       ...
    #     </packagelist>
    #   </group>

    def start_group_elem(self):
        self.current_unit = {"_content_type_id": "package_group"}
        self.units.append(self.current_unit)

    def handle_group_tag(self, tag, attrs):
        if self.handle_text_elem(tag, attrs):
            return

        elif tag in ("default", "uservisible"):
            self.current_buf = BooleanStringIO()
            if tag == "uservisible":
                tag = "user_visible"
            self.current_unit[tag] = self.current_buf

    def handle_group_packagelist(self, attrs):
        package_type = attrs.get("type") or "mandatory"
        key = package_type + "_package_names"
        self.current_buf = StringIO()
        target = self.current_unit.setdefault(key, [])

        if package_type == "conditional":
            # "conditional" type is special, a requires attrib is included, and Pulp
            # stores a (pkgname, requires) tuple.
            target.append([self.current_buf, attrs.get("requires")])
        else:
            # Anything else just stores the package name.
            target.append(self.current_buf)

    def handle_group_elem(self, path, attrs):
        if path == []:
            return self.start_group_elem()

        if len(path) == 1:
            return self.handle_group_tag(path[0], attrs)

        if path == ["packagelist", "packagereq"]:
            return self.handle_group_packagelist(attrs)

    ########################## Environment ################################
    #   <environment>
    #     <id>cloud-server-environment</id>
    #     <name>Fedora Cloud Server</name>
    #     <name xml:lang="af">Fedora-wolkbediener</name>
    #     <name xml:lang="bg">Fedora Cloud Сървър</name>
    #     ...
    #     <description>A server install with components needed...</description>
    #     <description xml:lang="af">’n Bedienerinstallasie met die nodige...</description>
    #     ...
    #     <display_order>3</display_order>
    #     <grouplist>
    #       <groupid>cloud-server</groupid>
    #       <groupid>core</groupid>
    #     </grouplist>
    #     <optionlist>
    #       <groupid>directory-server</groupid>
    #       <groupid>dns-server</groupid>
    #       ...
    #     </optionlist>
    #   </environment>

    def start_environment_elem(self):
        self.current_unit = {"_content_type_id": "package_environment"}
        self.units.append(self.current_unit)

    def handle_environment_tag(self, tag, attrs):
        if self.handle_text_elem(tag, attrs):
            return

        self.handle_display_order_tag(tag)

    def handle_environment_grouplist(self):
        self.current_buf = StringIO()
        self.current_unit.setdefault("group_ids", []).append(self.current_buf)

    def handle_environment_optionlist(self, attrs):
        self.current_buf = StringIO()

        option = {"group": self.current_buf}

        option["default"] = (attrs.get("default") or "").lower() == "true"

        self.current_unit.setdefault("options", []).append(option)

    def handle_environment_elem(self, path, attrs):
        if path == []:
            return self.start_environment_elem()

        if len(path) == 1:
            return self.handle_environment_tag(path[0], attrs)

        if path == ["grouplist", "groupid"]:
            return self.handle_environment_grouplist()

        if path == ["optionlist", "groupid"]:
            return self.handle_environment_optionlist(attrs)

    ########################## Category ###################################
    #   <category>
    #     <id>kde-desktop-environment</id>
    #     <name>KDE Desktop</name>
    #     <name xml:lang="af">KDE-werkskerm</name>
    #     <name xml:lang="as">KDE ডেস্কটপ</name>
    #     ...
    #     <description>The KDE SC includes ...</description>
    #     <description xml:lang="ar">الـ KDE SC يتضمن سطح...</description>
    #     <display_order>10</display_order>
    #     <grouplist>
    #       <groupid>kde-apps</groupid>
    #       <groupid>kde-desktop</groupid>
    #       ...
    #     </grouplist>
    #   </category>

    def start_category_elem(self):
        self.current_unit = {"_content_type_id": "package_category"}
        self.units.append(self.current_unit)

    def handle_category_tag(self, tag, attrs):
        if self.handle_text_elem(tag, attrs):
            return

        self.handle_display_order_tag(tag)

    def handle_category_grouplist(self):
        self.current_buf = StringIO()
        self.current_unit.setdefault("packagegroupids", []).append(self.current_buf)

    def handle_category_elem(self, path, attrs):
        if path == []:
            return self.start_category_elem()

        if len(path) == 1:
            return self.handle_category_tag(path[0], attrs)

        if path == ["grouplist", "groupid"]:
            return self.handle_category_grouplist()

    ####################### Langpacks #####################################
    # <langpacks>
    #     <match install="LabPlot-doc-%s" name="LabPlot-doc"/>
    #     <match install="aspell-%s" name="aspell"/>
    #     ...
    # </langpacks>

    def start_langpacks_elem(self):
        self.current_unit = {"_content_type_id": "package_langpacks"}
        self.units.append(self.current_unit)

    def handle_langpacks_match(self, attrs):
        self.current_unit.setdefault("matches", []).append(
            {"install": attrs.get("install"), "name": attrs.get("name")}
        )

    def handle_langpacks_elem(self, path, attrs):
        if path == []:
            return self.start_langpacks_elem()

        if path == ["match"]:
            return self.handle_langpacks_match(attrs)

    ####################### Handlers ######################################
    # All of these are installed on the expat parser.
    #
    # The name of each method must exactly match the names documented at
    # xml.parsers.expat.
    #
    # These handlers dispatch to the rest of the code above to parse elements
    # once the type is known.

    def StartElementHandler(self, name, attrs):
        self.current_path.append(name)

        prefix = self.current_path[:2]
        rest = self.current_path[2:]

        if prefix == ["comps", "group"]:
            return self.handle_group_elem(rest, attrs)

        if prefix == ["comps", "category"]:
            return self.handle_category_elem(rest, attrs)

        if prefix == ["comps", "environment"]:
            return self.handle_environment_elem(rest, attrs)

        if prefix == ["comps", "langpacks"]:
            return self.handle_langpacks_elem(rest, attrs)

    def CharacterDataHandler(self, data):
        self.current_buf.write(data)

    def EndElementHandler(self, _name):
        self.current_path = self.current_path[:-1]
        self.current_buf = StringIO()


def units_for_xml(io):
    """Parse comps.xml from a file-like object and return corresponding Pulp units.

    Arguments:
        io (file object)
            A file-like object.

            Should be opened in binary mode, and should point at bytes making up
            a valid comps.xml document encoded with UTF-8, UTF-16, ISO-8859-1 (Latin1)
            or ASCII.

    Returns:
        list[dict]
            A list of unit metadata in the form used by Pulp2 for unit types relating
            to comps.xml (e.g. package_group, package_langpacks, ...).

            Returned units omit the 'repo_id' attribute, which must be filled in if
            units will be uploaded to a specific repo.

    Note: this is the only function in this module intended to be used from other
    modules.
    """
    parser = CompsParser()
    return parser.parse(io)
