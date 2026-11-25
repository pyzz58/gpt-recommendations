import { redirect } from "next/navigation";

export default async function ProjectEntry({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/projects/${id}/overview`);
}
