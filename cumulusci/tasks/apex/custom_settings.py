""" a task for waiting on a specific custom settings value """

from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import SalesforceException
from simple_salesforce import SalesforceMalformedRequest
from cumulusci.core.utils import process_bool_arg


class CustomSettingValueWait(BaseSalesforceApiTask):
    """ CustomSettingValueWait polls an org until the specific value exists in a custom settings field """

    name = "CustomSettingValueWait"

    task_options = {
        "object": {
            "description": "Name of the Hierarchical Custom Settings object to query. Can include the %%%NAMESPACE%%% token. ",
            "required": True,
        },
        "field": {
            "description": "Name of the field on the Custom Settings to query. Can include the %%%NAMESPACE%%% token. ",
            "required": True,
        },
        "value": {
            "description": "Value of the field to wait for (String, Integer or Boolean). ",
            "required": True,
        },
        "poll_interval": {
            "description": (
                "Seconds to wait before polling for batch job completion. "
                "Defaults to 10 seconds."
            ),
        },
    }

    def _run_task(self):
        self.poll_interval_s = int(self.options.get("poll_interval", 10))

        self.object_name = self.options["object"]
        self.field_name = self.options["field"]
        self.check_value = self.options["value"]

        # Process namespace tokens
        namespace = self.project_config.project__package__namespace
        namespace_prefix = ""
        if namespace:
            namespace_prefix = namespace + "__"

        self.object_name = self.object_name.replace("%%%NAMESPACE%%%", namespace_prefix)
        self.field_name = self.field_name.replace("%%%NAMESPACE%%%", namespace_prefix)

        self._poll()  # will block until poll_complete

        self.logger.info("Value Matched.")

        return True

    def _poll_action(self):
        try:
            query_results = self.sf.query(self._object_query)
        except:
            print(
                "Only Hierarchical Custom Settings objects can be used with this task"
            )
            raise

        self.record = None
        for row in query_results["records"]:
            setupOwnerId = str(row["SetupOwnerId"])
            if setupOwnerId.startswith("00D"):
                self.record = row

        if not self.record:
            raise SalesforceException("Custom Settings Org Default record not found")

        self.poll_complete = not self._poll_again()

    def _poll_again(self):
        return not self.success

    @property
    def success(self):
        self.field_value = self.record[self.field_name]

        if isinstance(self.field_value, (bool)):
            self.check_value = process_bool_arg(self.check_value)
            self.field_value = process_bool_arg(self.field_value)
        elif isinstance(self.field_value, (int, float)):
            self.check_value = float(self.check_value)
            self.field_value = float(self.field_value)
        elif isinstance(field_value, (str)):
            self.check_value = str(self.check_value).lower()
            self.field_value = str(self.field_value).lower()

        self.logger.info(
            f"{self.field_name}: Looking for {self.check_value} and found {self.field_value}"
        )
        return self.field_value == self.check_value

    @property
    def _object_query(self):
        return f"SELECT SetupOwnerId, {self.field_name} FROM {self.object_name}"
