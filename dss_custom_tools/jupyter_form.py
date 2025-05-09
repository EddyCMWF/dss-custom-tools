import json
from typing import Any, Dict, List, Optional

import ipywidgets as widgets
from datapi import ApiClient
from IPython.display import clear_output, display


class DownloadForm:
    """Interactive selection form for collections in a Jupyter Notebook using ipywidgets.

    Automatically builds form widgets from a collection's metadata and tracks user selections.
    """

    def __init__(
        self,
        client: ApiClient = ApiClient(),
        output: Optional[widgets.Output] = None,
        dataset: Optional[str] = None,
        request: Optional[Dict[str, List[str]]] = None,
    ):
        """
        Initialize and display the form.

        Parameters
        ----------
        client : ApiClient
            An connected ApiClient.
        output : widgets.Output, optional
            Optional output widget to render the form in.
        dataset : str, optional
            Unused in current implementation.
        request : dict, optional
            Unused in current implementation.
        """
        self.client = client
        self.output = output or widgets.Output()
        self.collection_id: Optional[str] = None
        self.request: Dict[str, Any] = {}

        self.collections: List[str] = sorted(client.get_collections().collection_ids)
        self.collection_widget = widgets.Dropdown(
            options=self.collections,
            description="Dataset",
            value=None,
        )
        self.widget_defs: Dict[str, widgets.Widget] = {}
        self.selection_output = widgets.Output()

        self.collection_widget.observe(self._on_collection_change, names="value")

        if self.collection_widget.value:
            self._build_form(self.collection_widget.value)
        else:
            self._display_initial_prompt()

        self._update_selection_state()
        display(self.output)

    def _display_initial_prompt(self):
        self.output.clear_output()
        with self.output:
            display(
                widgets.VBox(
                    [
                        widgets.HTML("<b>Select a dataset to begin</b>"),
                        self.collection_widget,
                    ]
                )
            )

    def _build_form(self, collection_id: str):
        self.output.clear_output()
        self.selection_output.clear_output()
        self.widget_defs.clear()

        # Show loading message
        with self.output:
            loading_msg = widgets.HTML(
                "Please wait while your download form is created..."
            )
            display(loading_msg)

        collection = self.client.get_collection(collection_id)
        form_widgets = self._form_json_to_widgets_dict(collection.form)
        selection: Dict[str, List[str]] = {}

        def update_selection_display():
            json_str = json.dumps(selection, indent=2)
            with self.selection_output:
                clear_output()
                display(widgets.HTML(f"<pre>{json_str}</pre>"))

        def on_change(change):
            for key, widget in self.widget_defs.items():
                if hasattr(widget, "_get_value"):
                    selection[key] = widget._get_value()

            allowed_options = collection.apply_constraints(
                {k: v for k, v in selection.items() if v}
            )

            for key, values in allowed_options.items():
                f_widget = form_widgets.get(key, {})
                labels = f_widget.get("labels", {})
                if key in self.widget_defs:
                    widget = self.widget_defs[key]
                    if hasattr(widget, "children") and isinstance(
                        widget.children[1], widgets.GridBox
                    ):
                        for tb in widget.children[1].children:
                            tb.layout.display = "none"
                        for tb, opt in zip(
                            widget.children[1].children, f_widget["values"]
                        ):
                            if opt in values:
                                tb.layout.display = ""
                    elif isinstance(widget, widgets.RadioButtons):
                        widget.options = [(labels.get(v, v), v) for v in values]
                        if widget.value not in values:
                            widget.value = None
                    elif isinstance(widget, widgets.SelectMultiple):
                        widget.options = values
                        widget.value = tuple([x for x in selection[key] if x in values])

            self._update_selection_state()
            update_selection_display()

        for key, f_widget in form_widgets.items():
            widget_type = f_widget.get("type", "checkbox")
            options = f_widget["values"]
            labels = f_widget.get("labels", {})
            columns = f_widget.get("columns", 4)

            buttons = [
                widgets.ToggleButton(
                    value=False,
                    description=labels.get(opt, opt),
                    layout=widgets.Layout(width="auto"),
                    button_style="",
                )
                for opt in options
            ]

            if widget_type == "checkbox":

                def get_value(tb_list=buttons, opts=options):
                    return [opt for opt, tb in zip(opts, tb_list) if tb.value]

                for tb in buttons:
                    tb.observe(on_change, names="value")

            elif widget_type == "radio":
                f_widget["title"] = f"{f_widget['title']} (select one)"

                def on_radio_click(change, tb_list=buttons):
                    if change["new"]:
                        for tb in tb_list:
                            if tb is not change["owner"]:
                                tb.value = False
                        on_change(change)

                for tb in buttons:
                    tb.observe(
                        lambda change, tb_list=buttons: on_radio_click(change, tb_list),
                        names="value",
                    )

                def get_value(tb_list=buttons, opts=options):
                    for opt, tb in zip(opts, tb_list):
                        if tb.value:
                            return [opt]
                    return []

            else:
                raise ValueError(f"Unsupported widget type: {widget_type}")

            widget = widgets.VBox(
                [
                    widgets.HTML(f"<h3>{f_widget['title']}</h3>"),
                    widgets.GridBox(
                        children=buttons,
                        layout=widgets.Layout(
                            grid_template_columns=f"repeat({columns}, auto)"
                        ),
                    ),
                ]
            )

            default_values = f_widget.get("default", [])
            for tb, opt in zip(buttons, options):
                tb.value = opt in default_values

            widget._get_value = get_value
            self.widget_defs[key] = widget

        self._update_selection_state()

        with self.output:
            selection_box = widgets.Accordion(children=[self.selection_output])
            selection_box.set_title(0, "View current Selection")
            selection_box.selected_index = None  # collapsed by default
            self.output.clear_output()  # Clear loading message
            display(
                widgets.VBox(
                    [
                        self.collection_widget,
                        widgets.HTML(f"<h2>{collection.title}</h2>"),
                        *[self.widget_defs[key] for key in self.widget_defs],
                        widgets.HTML("<br>"),
                        selection_box,
                    ]
                )
            )

    def _on_collection_change(self, change):
        if change["name"] == "value" and change["new"] != change["old"]:
            self._build_form(change["new"])

    def _update_selection_state(self):
        self.collection_id = self.collection_widget.value
        self.request = {
            key: widget._get_value()
            for key, widget in self.widget_defs.items()
            if hasattr(widget, "_get_value") and widget._get_value()
        }

    def _form_json_to_widgets_dict(
        self,
        form: List[Dict[str, Any]],
        ignore_widget_names: List[str] = ["download_format", "data_format"],
        ignore_widget_types: List[str] = [
            "ExclusiveGroupWidget",
            "FreeEditionWidget",
            "GeographicExtentWidget",
            "GeographicLocationWidget",
            "LicenceWidget",
        ],
    ) -> Dict[str, Any]:
        out_widgets = {}
        widget_map = {
            "StringListWidget": "checkbox",
            "StringListArrayWidget": "checkbox",
            "StringChoiceWidget": "radio",
        }
        for widget in form:
            widget_name = widget.get("name", "")
            widget_type = widget.get("type", "")
            if widget_name in ignore_widget_names or widget_type in ignore_widget_types:
                continue
            if widget_name in out_widgets:
                continue
            out_widgets[widget_name] = {
                k: widget[k] for k in ["label", "type"] if k in widget
            }
            details = widget.get("details", {})
            if "groups" in details:
                labels = {}
                values = []
                columns = 1
                for group in details["groups"]:
                    labels.update(group.get("labels", {}))
                    values += [v for v in group.get("values", []) if v not in values]
                    columns = max(columns, group.get("columns", 1))
            else:
                labels = details.get("labels", {})
                values = details.get("values", [])
                columns = details.get("columns", 1)
            out_widgets[widget_name]["labels"] = labels
            out_widgets[widget_name]["values"] = values
            out_widgets[widget_name]["title"] = widget.get("label", "")
            out_widgets[widget_name]["type"] = widget_map.get(widget_type, widget_type)
            out_widgets[widget_name]["columns"] = columns
            if "default" in details:
                out_widgets[widget_name]["default"] = details["default"]
        return out_widgets

    def debug(self):
        """Print the current internal state of the form."""
        print("Collection ID:", self.collection_id)
        print("Request:")
        print(json.dumps(self.request, indent=2))
