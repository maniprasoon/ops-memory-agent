export type MemoryCard = {
  id: string;
  title: string;
  date: string;
  score: number;
  body: string;
};

export function parseMemory(memory: string, index: number): MemoryCard {
  const titleFromField = memory.match(/title:\s*(.+)/i)?.[1]?.trim();
  const incidentLine = memory
    .split("\n")
    .map((line) => line.trim())
    .find((line) => line.length > 0 && !line.toLowerCase().startsWith("memory_id:"));
  const firstSentence = memory.split(/[.|]/)[0]?.replace(/^Past incident \d+:\s*/i, "").trim();
  const title = titleFromField ?? incidentLine ?? firstSentence ?? "Related production incident";
  const date = memory.match(/When:\s*([^|.\n]+)/i)?.[1]?.trim() ?? "Recent memory";
  const score = Math.max(72, 96 - index * 6);

  return {
    id: `${index}-${title}`,
    title,
    date,
    score,
    body: memory
  };
}

export function parseMemories(memories: string[]): MemoryCard[] {
  return memories.map((memory, index) => parseMemory(memory, index));
}

