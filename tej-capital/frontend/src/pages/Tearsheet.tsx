import { useParams } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";

export default function Tearsheet() {
  const { month } = useParams<{ month: string }>();
  return (
    <EmptyState
      title="Tearsheet"
      body={`The printable factsheet for ${month ?? "this month"} lands here in Task 29.`}
    />
  );
}
