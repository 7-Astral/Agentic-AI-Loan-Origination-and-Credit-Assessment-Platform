"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import {
  getAuditEvents,
  getDocumentRequirements,
  getDocumentTypes,
  getLoanTypes,
  getPolicyVersions,
  getProducts,
  getRules,
} from "@/lib/mock/admin-data";
import type {
  AdminAuditEvent,
  AdminCategory,
  AdminChangeAuditEvent,
  AdminDocumentType,
  AdminLoanPolicyRow,
  AdminLoanType,
  AdminPolicyVersion,
  AdminProduct,
  AdminRule,
} from "@/lib/types/admin";

interface AdminBankData {
  loanTypes: AdminLoanType[];
  products: AdminProduct[];
  documentTypes: AdminDocumentType[];
  documentRequirements: { loanTypeCode: string; categoryCode: string; documentTypeCode: string }[];
  policyVersions: AdminPolicyVersion[];
  rules: AdminRule[];
  auditLog: AdminAuditEvent[];
}

interface AdminDataContextValue extends AdminBankData {
  addLoanType: (loanType: { code: string; name: string; description: string }) => void;
  updateLoanType: (code: string, patch: { name: string; description: string }) => void;
  addCategory: (loanTypeCode: string, category: AdminCategory) => void;
  renameCategory: (loanTypeCode: string, categoryCode: string, name: string) => void;

  addProduct: (product: AdminProduct) => void;
  updateProduct: (productCode: string, product: AdminProduct) => void;
  deleteProduct: (productCode: string) => void;

  addDocumentType: (docType: AdminDocumentType) => void;
  toggleDocumentRequirement: (documentTypeCode: string, loanTypeCode: string, categoryCode: string) => void;

  /**
   * Appends a brand-new immutable policy version and flips whatever was previously "active"
   * to "superseded" — there is deliberately no way to edit an existing version's fields.
   */
  createPolicyVersion: (input: {
    version: string;
    effectiveFrom: string;
    notes: string;
    loanPolicyRows: AdminLoanPolicyRow[];
  }) => AdminPolicyVersion;

  addRule: (rule: AdminRule) => void;
  updateRule: (ruleId: string, rule: AdminRule) => void;
  deleteRule: (ruleId: string) => void;
}

const AdminDataContext = createContext<AdminDataContextValue | null>(null);

function seedData(bankId: string): AdminBankData {
  return {
    loanTypes: getLoanTypes(bankId),
    products: getProducts(bankId),
    documentTypes: getDocumentTypes(bankId),
    documentRequirements: getDocumentRequirements(bankId),
    policyVersions: getPolicyVersions(bankId),
    rules: getRules(bankId),
    auditLog: getAuditEvents(bankId),
  };
}

function storageKey(bankId: string): string {
  return `admin:data:${bankId}`;
}

function changeEvent(entity: string, action: AdminChangeAuditEvent["action"], summary: string): AdminChangeAuditEvent {
  return {
    id: `chg-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
    type: "admin_change",
    timestamp: new Date().toISOString(),
    summary,
    entity,
    action,
    actor: "admin (this session)",
  };
}

export function AdminDataProvider({ bankId, children }: { bankId: string; children: ReactNode }) {
  const [data, setData] = useState<AdminBankData>(() => seedData(bankId));
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const raw = window.localStorage.getItem(storageKey(bankId));
    const seed = seedData(bankId);
    if (raw) {
      try {
        setData({ ...seed, ...(JSON.parse(raw) as Partial<AdminBankData>) });
      } catch {
        setData(seed);
      }
    } else {
      setData(seed);
    }
    setHydrated(true);
  }, [bankId]);

  useEffect(() => {
    if (!hydrated) return;
    window.localStorage.setItem(storageKey(bankId), JSON.stringify(data));
  }, [bankId, data, hydrated]);

  const value: AdminDataContextValue = {
    ...data,

    addLoanType(loanType) {
      setData((prev) => ({
        ...prev,
        loanTypes: [...prev.loanTypes, { ...loanType, categories: [] }],
        auditLog: [changeEvent("Loan Type", "created", `Loan type "${loanType.name}" created`), ...prev.auditLog],
      }));
    },
    updateLoanType(code, patch) {
      setData((prev) => ({
        ...prev,
        loanTypes: prev.loanTypes.map((lt) => (lt.code === code ? { ...lt, ...patch } : lt)),
        auditLog: [changeEvent("Loan Type", "updated", `Loan type "${patch.name}" updated`), ...prev.auditLog],
      }));
    },
    addCategory(loanTypeCode, category) {
      setData((prev) => ({
        ...prev,
        loanTypes: prev.loanTypes.map((lt) =>
          lt.code === loanTypeCode ? { ...lt, categories: [...lt.categories, category] } : lt,
        ),
        auditLog: [changeEvent("Category", "created", `Category "${category.name}" added`), ...prev.auditLog],
      }));
    },
    renameCategory(loanTypeCode, categoryCode, name) {
      setData((prev) => ({
        ...prev,
        loanTypes: prev.loanTypes.map((lt) =>
          lt.code === loanTypeCode
            ? { ...lt, categories: lt.categories.map((c) => (c.code === categoryCode ? { ...c, name } : c)) }
            : lt,
        ),
        auditLog: [changeEvent("Category", "updated", `Category renamed to "${name}"`), ...prev.auditLog],
      }));
    },

    addProduct(product) {
      setData((prev) => ({
        ...prev,
        products: [...prev.products, product],
        auditLog: [changeEvent("Product", "created", `Product "${product.name}" created`), ...prev.auditLog],
      }));
    },
    updateProduct(productCode, product) {
      setData((prev) => ({
        ...prev,
        products: prev.products.map((p) => (p.productCode === productCode ? product : p)),
        auditLog: [changeEvent("Product", "updated", `Product "${product.name}" updated`), ...prev.auditLog],
      }));
    },
    deleteProduct(productCode) {
      setData((prev) => {
        const removed = prev.products.find((p) => p.productCode === productCode);
        return {
          ...prev,
          products: prev.products.filter((p) => p.productCode !== productCode),
          auditLog: [
            changeEvent("Product", "deleted", `Product "${removed?.name ?? productCode}" deleted`),
            ...prev.auditLog,
          ],
        };
      });
    },

    addDocumentType(docType) {
      setData((prev) => ({
        ...prev,
        documentTypes: [...prev.documentTypes, docType],
        auditLog: [
          changeEvent("Document Type", "created", `Document type "${docType.name}" created`),
          ...prev.auditLog,
        ],
      }));
    },
    toggleDocumentRequirement(documentTypeCode, loanTypeCode, categoryCode) {
      setData((prev) => {
        const exists = prev.documentRequirements.some(
          (req) =>
            req.documentTypeCode === documentTypeCode &&
            req.loanTypeCode === loanTypeCode &&
            req.categoryCode === categoryCode,
        );
        const docTypeName = prev.documentTypes.find((d) => d.code === documentTypeCode)?.name ?? documentTypeCode;
        return {
          ...prev,
          documentRequirements: exists
            ? prev.documentRequirements.filter(
                (req) =>
                  !(
                    req.documentTypeCode === documentTypeCode &&
                    req.loanTypeCode === loanTypeCode &&
                    req.categoryCode === categoryCode
                  ),
              )
            : [...prev.documentRequirements, { documentTypeCode, loanTypeCode, categoryCode }],
          auditLog: [
            changeEvent(
              "Document Requirement",
              exists ? "deleted" : "created",
              `"${docTypeName}" ${exists ? "no longer required" : "marked required"} for ${loanTypeCode}/${categoryCode}`,
            ),
            ...prev.auditLog,
          ],
        };
      });
    },

    createPolicyVersion(input) {
      const created: AdminPolicyVersion = {
        id: `v-${Date.now().toString(36)}`,
        version: input.version,
        status: "active",
        effectiveFrom: input.effectiveFrom,
        createdAt: new Date().toISOString().slice(0, 10),
        notes: input.notes,
        loanPolicyRows: input.loanPolicyRows,
      };
      setData((prev) => ({
        ...prev,
        policyVersions: [
          ...prev.policyVersions.map((pv) =>
            pv.status === "active" ? { ...pv, status: "superseded" as const } : pv,
          ),
          created,
        ],
        auditLog: [
          changeEvent("Policy Version", "created", `Policy version "${created.version}" created and made active`),
          ...prev.auditLog,
        ],
      }));
      return created;
    },

    addRule(rule) {
      setData((prev) => ({
        ...prev,
        rules: [...prev.rules, rule],
        auditLog: [changeEvent("Rule", "created", `Rule "${rule.ruleId}" added to ${rule.framework}`), ...prev.auditLog],
      }));
    },
    updateRule(ruleId, rule) {
      setData((prev) => ({
        ...prev,
        rules: prev.rules.map((r) => (r.ruleId === ruleId ? rule : r)),
        auditLog: [changeEvent("Rule", "updated", `Rule "${ruleId}" updated`), ...prev.auditLog],
      }));
    },
    deleteRule(ruleId) {
      setData((prev) => ({
        ...prev,
        rules: prev.rules.filter((r) => r.ruleId !== ruleId),
        auditLog: [changeEvent("Rule", "deleted", `Rule "${ruleId}" deleted`), ...prev.auditLog],
      }));
    },
  };

  return <AdminDataContext.Provider value={value}>{children}</AdminDataContext.Provider>;
}

export function useAdminData(): AdminDataContextValue {
  const ctx = useContext(AdminDataContext);
  if (!ctx) throw new Error("useAdminData must be used within AdminDataProvider");
  return ctx;
}
