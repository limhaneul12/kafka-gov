export const GOVERNANCE_PRESETS = [
    {
        id: "strict-prod",
        name: "Strict Production (Shield)",
        description: "Maximum safety for production environments. Enforces documentation, strict naming, and backward compatibility.",
        content: {
            rules: {
                MISSING_DOC: { enabled: true, severity: "error" },
                INVALID_FIELD_NAME: { enabled: true, severity: "error", pattern: "^[a-z_][a-z0-9_]*$" },
                INVALID_RECORD_NAME: { enabled: true, severity: "error", pattern: "^[A-Z][a-zA-Z0-9]*$" },
                NULLABLE_WITHOUT_DEFAULT: { enabled: true, severity: "error" },
            },
            guardrails: {
                allowed_compatibility: ["BACKWARD", "BACKWARD_TRANSITIVE", "FULL", "FULL_TRANSITIVE"],
                enforce_owner: true,
            },
        },
    },
    {
        id: "standard-team",
        name: "Standard Team (Standard)",
        description: "Recommended for shared team subjects. Balanced linting and compatibility rules.",
        content: {
            rules: {
                MISSING_DOC: { enabled: true, severity: "warning" },
                INVALID_FIELD_NAME: { enabled: true, severity: "warning", pattern: "^[a-z_][a-z0-9_]*$" },
                NULLABLE_WITHOUT_DEFAULT: { enabled: true, severity: "warning" },
            },
            guardrails: {
                allowed_compatibility: ["BACKWARD", "FORWARD", "FULL", "NONE"],
            },
        },
    },
    {
        id: "experimental",
        name: "Fast Experimental (Minimal)",
        description: "Minimal restrictions for fast iteration in dev/sandbox environments.",
        content: {
            rules: {
                MISSING_DOC: { enabled: false },
            },
            guardrails: {
                allowed_compatibility: ["ANY"],
            },
        },
    },
];
