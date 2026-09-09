import { redirect } from "next/navigation";

export default function BankIndexPage({ params }: { params: { bankId: string } }) {
  redirect(`/admin/banks/${params.bankId}/dashboard`);
}
