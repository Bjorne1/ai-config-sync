"""Page widget exports for the main dashboard window."""

from .cleanup_page import CleanupPage
from .config_page import ConfigPage
from .overview_page import OverviewPage
from .resource_page import ResourcePage
from .tools_page import ToolsPage
from .workflow_page import WorkflowPage

__all__ = [
    "CleanupPage",
    "ConfigPage",
    "OverviewPage",
    "ResourcePage",
    "ToolsPage",
    "WorkflowPage",
]
