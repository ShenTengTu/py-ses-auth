"""
https://gist.github.com/ShenTengTu/5e40217db8f7a218b28f365a13a14c00
"""

__all__ = ["arg_meta", "CLI"]

import argparse


def arg_meta(*arg_flags, **arg_conf):
    """
    Return a tuple `(arg_flags, arg_conf)` that contains argument flags & argument config.
    `arg_flags`:  A tuple contains argument flags
    `arg_conf`: A dict containsf argument config
    """
    return (arg_flags, arg_conf)


class CLI(argparse.ArgumentParser):
    """
    Custom Argument Parser
    """

    def __init__(self, version: str, main_params: dict, sub_params: dict):
        # record name of the attribute under which sub-command name will be stored
        self._sub_dest_name = sub_params.get("dest")
        if self._sub_dest_name is None:
            sub_params["dest"] = "sub_command"
            self._sub_dest_name = sub_params["dest"]

        # handler mapping
        self._sub_parser_handler_map = {}
        self._sub_parser_alias_map = {}
        self._argument_group_metadata_map = {}

        super().__init__(**main_params)

        # Fix TypeError: __init__() got an unexpected keyword argument
        # `parser_class=argparse.ArgumentParser`
        if "parser_class" not in sub_params:
            sub_params["parser_class"] = argparse.ArgumentParser
        self._sub_parsers_action = self.add_subparsers(**sub_params)

        # Add `version` argument
        self.add_argument(
            "-v",
            "--version",
            action="version",
            version=version,
            help="Display the version of CLI.",
        )

    def sub_command(self, **kwargs):
        """
        Decorator.
        - Add sub parser with the same name as the function.
        - Register the function as the handler of the sub parser
        """

        def deco(fn):
            fn_name = fn.__name__
            self._sub_parser_handler_map[fn_name] = fn
            if "aliases" in kwargs:
                for alias in kwargs["aliases"]:
                    self._sub_parser_alias_map[alias] = fn_name
            self._sub_parsers_action.add_parser(fn_name, **kwargs)

            return fn

        return deco

    def sub_command_arg(self, *arg_flags, **arg_conf):
        """
        Decorator.
        - Add an argument to the sub parser with the same name as the function.
        """

        def deco(fn):
            parser = self._sub_parsers_action._name_parser_map[fn.__name__]
            parser.add_argument(*arg_flags, **arg_conf)
            return fn

        return deco

    def arg_group(self, title):
        """
        Decorator.
        - Add an argument group to the sub parser by given title.
        """

        def deco(fn):
            metadata = self._argument_group_metadata_map.get(title, None)
            if metadata:
                description, list_of_arg_conf = metadata
                parser = self._sub_parsers_action._name_parser_map[fn.__name__]
                g = parser.add_argument_group(title, description)
                for arg_flags, arg_conf in list_of_arg_conf:
                    g.add_argument(*arg_flags, **arg_conf)

        return deco

    def register_argument_group(self, title, description=None, list_of_arg_conf=[]):
        """
        Register an argument group by given title and related metadata.
        """
        self._argument_group_metadata_map[title] = (description, list_of_arg_conf)

    def handle_args(self, args=None, namespace=None):
        """
        Parse args then pass to handler
        """
        namespace = self.parse_args(args, namespace)
        sub_parser_name = getattr(namespace, self._sub_dest_name, None)
        if sub_parser_name is not None:
            fn = self._sub_parser_handler_map.get(sub_parser_name)
            if fn is None:
                fn_name = self._sub_parser_alias_map.get(sub_parser_name)
                fn = self._sub_parser_handler_map.get(fn_name)
            if callable(fn):
                fn(namespace)
        return namespace
