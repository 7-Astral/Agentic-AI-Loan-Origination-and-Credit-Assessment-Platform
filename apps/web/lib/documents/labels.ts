import { prettify } from "@/lib/playground/fields";
import type { DocumentCheck, ExtractedField } from "@/lib/types/documents";

export const CATEGORY_LABELS: Record<string, string> = {
  exp_food_groceries: "Food and groceries",
  exp_clothing_personal_care: "Clothing and personal care",
  exp_recreation_holidays: "Recreation and holidays",
  exp_education_childcare: "Education and childcare",
  exp_insurance: "Insurance",
  exp_medical_health: "Medical and health",
  exp_rent_board: "Rent or board",
  exp_other_housing: "Other housing",
  exp_phone_internet_media: "Phone, internet and media",
  exp_vehicle_transport: "Vehicle and transport",
  income: "Income",
  transfer: "Transfer",
  other: "Other",
};

export const categoryLabel = (category: string | null) =>
  category === null ? "Not categorised" : (CATEGORY_LABELS[category] ?? prettify(category));

const aud = (value: number, digits = 2) =>
  new Intl.NumberFormat("en-AU", {
    style: "currency",
    currency: "AUD",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);

export const money = (value: number) => aud(value, Number.isInteger(value) ? 0 : 2);

function formatDate(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!match) return iso;
  const [, year, month, day] = match;
  return new Date(Number(year), Number(month) - 1, Number(day)).toLocaleDateString("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatField(field: ExtractedField): string {
  if (field.value === null || field.value === undefined) return "";
  if (field.type === "currency" && typeof field.value === "number") return aud(field.value);
  if (field.type === "date" && typeof field.value === "string") return formatDate(field.value);
  return String(field.value);
}

export const FIELD_LABELS: Record<string, string> = {
  full_name: "Full name",
  date_of_birth: "Date of birth",
  document_number: "Document number",
  expiry_date: "Expiry date",
  name_on_document: "Name on document",
  address: "Address",
  document_date: "Document date",
  employee_name: "Employee",
  employer_name: "Employer",
  gross_pay_this_period: "Gross pay this period",
  pay_period_start: "Pay period start",
  pay_period_end: "Pay period end",
  pay_frequency: "Pay frequency",
  account_holder_name: "Account holder",
  statement_period_start: "Statement start",
  statement_period_end: "Statement end",
  closing_balance: "Closing balance",
  abn: "ABN",
  acn: "ACN",
  cogs: "Cost of goods sold",
  ebitda: "EBITDA",
};

export const fieldLabel = (id: string) => FIELD_LABELS[id] ?? prettify(id);

export function describeCheck(compare: DocumentCheck["compare"] | null, tolerance: number | null): string {
  if (compare === "exact") return "Must match exactly";
  if (compare === "fuzzy_text") return "Wording can differ slightly (80% similar counts as a match)";
  if (compare === "currency_tolerance") return `Must be within ${tolerance ?? 5}%`;
  return "";
}
