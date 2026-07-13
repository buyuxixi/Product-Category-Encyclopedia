import type { Metadata } from "next";
import EncyclopediaClient from "./EncyclopediaClient";

export const metadata: Metadata = {
  title: "产品品类百科 | Category Intelligence",
  description: "把复杂品类，讲成清晰决策。面向产品、选品与研究工作的公开品类知识库。",
};

export default function Home() {
  return <EncyclopediaClient />;
}
