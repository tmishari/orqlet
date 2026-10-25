"""Every contract Orqlet reads or writes, keyed by schema id."""

from orqlet.application.contracts.artifact_header import ArtifactHeader
from orqlet.application.contracts.as_is import AsIsArtifact, AsIsFragment
from orqlet.application.contracts.cli_result import CliResult
from orqlet.application.contracts.common import Contract
from orqlet.application.contracts.design_set import DesignSet
from orqlet.application.contracts.finding import Finding
from orqlet.application.contracts.generated_lock import GeneratedLock
from orqlet.application.contracts.integrations import Integrations
from orqlet.application.contracts.knowledge_config import DocsMap, KnowledgeConfig
from orqlet.application.contracts.knowledge_impact import KnowledgeImpact
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.contracts.module_card import ModuleCard
from orqlet.application.contracts.plan import ImplementationPlan
from orqlet.application.contracts.policy import WorkflowPolicy
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.contracts.question_ledger import QuestionLedger
from orqlet.application.contracts.review_input import ReviewInput
from orqlet.application.contracts.review_result import ReviewResult
from orqlet.application.contracts.role_bindings import RoleBindings
from orqlet.application.contracts.self_check import SelfCheck
from orqlet.application.contracts.standards_lock import StandardsLock
from orqlet.application.contracts.standards_pack import PackManifest, RuleFile
from orqlet.application.contracts.test_record import TesterRecord
from orqlet.application.contracts.versions_file import Versions
from orqlet.application.contracts.workflow_package import (
    ExemptClasses,
    Released,
    ReleaseHistory,
    WorkflowIdentity,
    WorkflowLock,
    WorkflowManifest,
    WorkflowRuleMeta,
)

CONTRACTS: dict[str, type[Contract]] = {
    "orqlet.project-profile/v1": ProjectProfile,
    "orqlet.workflow-policy/v2": WorkflowPolicy,
    "orqlet.model-policy/v1": ModelPolicy,
    "orqlet.integrations/v1": Integrations,
    "orqlet.generated-lock/v1": GeneratedLock,
    "orqlet.versions/v1": Versions,
    "orqlet.role-bindings/v1": RoleBindings,
    "orqlet.standards-lock/v1": StandardsLock,
    "orqlet.standards-pack/v1": PackManifest,
    "orqlet.rules/v1": RuleFile,
    "orqlet.cli-result/v1": CliResult,
    "orqlet.workflow-identity/v1": WorkflowIdentity,
    "orqlet.workflow-manifest/v1": WorkflowManifest,
    "orqlet.workflow-releases/v1": ReleaseHistory,
    "orqlet.exempt/v1": ExemptClasses,
    "orqlet.workflow-rule/v1": WorkflowRuleMeta,
    "orqlet.workflow-lock/v1": WorkflowLock,
    "orqlet.released/v1": Released,
    "orqlet.artifact-header/v1": ArtifactHeader,
    "orqlet.as-is/v1": AsIsArtifact,
    "orqlet.as-is-fragment/v1": AsIsFragment,
    "orqlet.design-set/v1": DesignSet,
    "orqlet.implementation-plan/v1": ImplementationPlan,
    "orqlet.question-ledger/v1": QuestionLedger,
    "orqlet.self-check/v1": SelfCheck,
    "orqlet.finding/v1": Finding,
    "orqlet.review-input/v1": ReviewInput,
    "orqlet.review-result/v1": ReviewResult,
    "orqlet.test-record/v1": TesterRecord,
    "orqlet.knowledge-impact/v1": KnowledgeImpact,
    "orqlet.module-card/v1": ModuleCard,
    "orqlet.knowledge/v2": KnowledgeConfig,
    "orqlet.docs-map/v1": DocsMap,
}
