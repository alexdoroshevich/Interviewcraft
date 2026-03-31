"use client";

import { useRef, useState, useCallback, useEffect } from "react";

// Codapi (codapi.org) — free, no auth, full stdlib, supports all 7 languages
const LANGUAGES = [
  { id: "python",     label: "Python",     ext: "py",   sandbox: "python",     file: "main.py"    },
  { id: "javascript", label: "JavaScript", ext: "js",   sandbox: "javascript", file: "main.js"    },
  { id: "typescript", label: "TypeScript", ext: "ts",   sandbox: "typescript", file: "main.ts"    },
  { id: "java",       label: "Java",       ext: "java", sandbox: "java",       file: "Main.java"  },
  { id: "go",         label: "Go",         ext: "go",   sandbox: "go",         file: "main.go"    },
  { id: "cpp",        label: "C++",        ext: "cpp",  sandbox: "cpp",        file: "main.cpp"   },
  { id: "rust",       label: "Rust",       ext: "rs",   sandbox: "rust",       file: "main.rs"    },
];

const STARTERS: Record<string, string> = {
  python:
`def solution(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        diff = target - n
        if diff in seen:
            return [seen[diff], i]
        seen[n] = i
    return []

# Test
print(solution([2, 7, 11, 15], 9))  # [0, 1]
`,
  javascript:
`function solution(nums, target) {
  const seen = new Map();
  for (let i = 0; i < nums.length; i++) {
    const diff = target - nums[i];
    if (seen.has(diff)) return [seen.get(diff), i];
    seen.set(nums[i], i);
  }
  return [];
}

console.log(solution([2, 7, 11, 15], 9)); // [0, 1]
`,
  typescript:
`function solution(nums: number[], target: number): number[] {
  const seen = new Map<number, number>();
  for (let i = 0; i < nums.length; i++) {
    const diff = target - nums[i];
    if (seen.has(diff)) return [seen.get(diff)!, i];
    seen.set(nums[i], i);
  }
  return [];
}

console.log(solution([2, 7, 11, 15], 9));
`,
  java:
`import java.util.*;

class Main {
  static int[] twoSum(int[] nums, int target) {
    Map<Integer, Integer> seen = new HashMap<>();
    for (int i = 0; i < nums.length; i++) {
      int diff = target - nums[i];
      if (seen.containsKey(diff)) return new int[]{seen.get(diff), i};
      seen.put(nums[i], i);
    }
    return new int[]{};
  }

  public static void main(String[] args) {
    System.out.println(Arrays.toString(twoSum(new int[]{2,7,11,15}, 9)));
  }
}
`,
  go:
`package main

import "fmt"

func solution(nums []int, target int) []int {
  seen := make(map[int]int)
  for i, n := range nums {
    diff := target - n
    if j, ok := seen[diff]; ok {
      return []int{j, i}
    }
    seen[n] = i
  }
  return nil
}

func main() {
  fmt.Println(solution([]int{2, 7, 11, 15}, 9)) // [0 1]
}
`,
  cpp:
`#include <iostream>
#include <vector>
#include <unordered_map>
using namespace std;

vector<int> solution(vector<int>& nums, int target) {
  unordered_map<int, int> seen;
  for (int i = 0; i < nums.size(); i++) {
    int diff = target - nums[i];
    if (seen.count(diff)) return {seen[diff], i};
    seen[nums[i]] = i;
  }
  return {};
}

int main() {
  vector<int> nums = {2, 7, 11, 15};
  auto res = solution(nums, 9);
  cout << "[" << res[0] << ", " << res[1] << "]" << endl;
}
`,
  rust:
`use std::collections::HashMap;

fn solution(nums: &[i32], target: i32) -> Vec<usize> {
    let mut seen: HashMap<i32, usize> = HashMap::new();
    for (i, &n) in nums.iter().enumerate() {
        let diff = target - n;
        if let Some(&j) = seen.get(&diff) {
            return vec![j, i];
        }
        seen.insert(n, i);
    }
    vec![]
}

fn main() {
    println!("{:?}", solution(&[2, 7, 11, 15], 9)); // [0, 1]
}
`,
};

interface CodeNotebookProps {
  onSendToChat?: (code: string, language: string) => void;
  onCodeChange?: (code: string, language: string, output?: string) => void;
}

export function CodeNotebook({ onSendToChat, onCodeChange }: CodeNotebookProps) {
  const [lang, setLang] = useState("python");
  const [code, setCode] = useState(STARTERS["python"]);
  const [output, setOutput] = useState<string>("");
  const [outputType, setOutputType] = useState<"idle" | "success" | "error" | "running">("idle");
  const [copied, setCopied] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Notify parent of code/output changes (debounced 2s) so the AI interviewer
  // can update its context without flooding on every keystroke.
  useEffect(() => {
    if (!onCodeChange) return;
    const timer = setTimeout(
      () => onCodeChange(code, lang, outputType !== "idle" ? output : undefined),
      2000,
    );
    return () => clearTimeout(timer);
  }, [code, lang, output, outputType, onCodeChange]);

  function handleLangChange(newLang: string) {
    if (code === STARTERS[lang] || code.trim() === "") {
      setCode(STARTERS[newLang] ?? "");
    }
    setLang(newLang);
    setOutput("");
    setOutputType("idle");
  }

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const textarea = textareaRef.current!;
    const { selectionStart, selectionEnd } = textarea;
    if (e.key === "Tab") {
      e.preventDefault();
      const newCode = code.substring(0, selectionStart) + "  " + code.substring(selectionEnd);
      setCode(newCode);
      setTimeout(() => { textarea.selectionStart = textarea.selectionEnd = selectionStart + 2; }, 0);
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      const lineStart = code.lastIndexOf("\n", selectionStart - 1) + 1;
      const currentLine = code.substring(lineStart, selectionStart);
      const indent = currentLine.match(/^(\s*)/)?.[1] ?? "";
      const extra = /[:{([]\s*$/.test(currentLine.trimEnd()) ? "  " : "";
      const insert = "\n" + indent + extra;
      const newCode = code.substring(0, selectionStart) + insert + code.substring(selectionEnd);
      setCode(newCode);
      setTimeout(() => { const pos = selectionStart + insert.length; textarea.selectionStart = textarea.selectionEnd = pos; }, 0);
    }
  }, [code]);

  async function runCode() {
    setOutputType("running");
    setOutput("Running...");
    const langInfo = LANGUAGES.find((l) => l.id === lang)!;
    try {
      const res = await fetch("https://codapi.org/api/v1/exec", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sandbox: langInfo.sandbox,
          command: "run",
          files: { [langInfo.file]: code },
        }),
      });
      if (!res.ok) {
        const text = await res.text();
        setOutput(`Runner error (${res.status}): ${text.slice(0, 300)}`);
        setOutputType("error");
        return;
      }
      const data = await res.json();
      const stdout = (data.stdout ?? "").trim();
      const stderr = (data.stderr ?? "").trim();
      const out = stdout || stderr || "(no output)";
      setOutput(out);
      setOutputType(data.ok && !stderr ? "success" : "error");
    } catch {
      setOutput("Could not reach code runner. Check your connection.");
      setOutputType("error");
    }
  }

  function handleCopy() {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const lineCount = code.split("\n").length;

  return (
    <div className="flex flex-col h-full font-mono text-xs bg-slate-950">
      {/* Header bar */}
      <div className="shrink-0 flex items-center gap-2 px-3 py-2 bg-slate-900 border-b border-slate-700 flex-wrap sm:flex-nowrap">
        <div className="flex gap-1.5 shrink-0">
          <div className="w-3 h-3 rounded-full bg-red-500/70" />
          <div className="w-3 h-3 rounded-full bg-amber-500/70" />
          <div className="w-3 h-3 rounded-full bg-green-500/70" />
        </div>
        <select
          value={lang}
          onChange={(e) => handleLangChange(e.target.value)}
          className="flex-1 min-w-[80px] text-xs bg-slate-800 border border-slate-600 rounded px-2 py-2 sm:py-1 text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-400 min-h-[36px]"
        >
          {LANGUAGES.map((l) => (
            <option key={l.id} value={l.id}>{l.label}</option>
          ))}
        </select>
        <button onClick={handleCopy} className="text-xs px-3 py-2 sm:py-1 rounded bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors min-h-[36px]">
          {copied ? "✓" : "Copy"}
        </button>
        <button
          onClick={runCode}
          disabled={outputType === "running"}
          className="text-xs px-3 py-2 sm:py-1 rounded bg-green-600 text-white hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-sans font-medium flex items-center gap-1.5 min-h-[36px]"
        >
          {outputType === "running" ? (
            <><span className="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Running</>
          ) : (
            <>▶ Run</>
          )}
        </button>
      </div>

      {/* Editor + line numbers */}
      <div className="flex flex-1 overflow-hidden min-h-0">
        <div className="w-10 shrink-0 pt-3 pb-3 text-right pr-2 text-slate-600 leading-[1.6rem] overflow-hidden select-none bg-slate-900 border-r border-slate-700/50">
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i} className="pr-1">{i + 1}</div>
          ))}
        </div>
        <textarea
          ref={textareaRef}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={handleKeyDown}
          spellCheck={false}
          className="flex-1 resize-none bg-slate-950 text-slate-100 py-3 px-3 leading-[1.6rem] focus:outline-none placeholder:text-slate-600 overflow-auto"
          placeholder="Write your solution..."
        />
      </div>

      {/* Output panel */}
      {outputType !== "idle" && (
        <div className={`shrink-0 border-t font-sans ${
          outputType === "success" ? "border-green-800 bg-green-950/50" :
          outputType === "error" ? "border-red-800 bg-red-950/50" :
          "border-slate-700 bg-slate-900"
        }`}>
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-slate-700/50">
            <span className={`text-xs font-semibold ${
              outputType === "success" ? "text-green-400" :
              outputType === "error" ? "text-red-400" :
              "text-slate-400"
            }`}>
              {outputType === "running" ? "Running..." : outputType === "success" ? "✓ Output" : "✗ Error / Output"}
            </span>
            <button onClick={() => setOutputType("idle")} className="text-slate-500 hover:text-slate-300 text-xs">✕</button>
          </div>
          <pre className="px-3 py-2 text-xs text-slate-300 max-h-24 sm:max-h-36 overflow-y-auto whitespace-pre-wrap leading-relaxed">
            {output}
          </pre>
        </div>
      )}

      {/* Footer */}
      <div className="shrink-0 px-3 py-2 bg-slate-900 border-t border-slate-700 flex gap-2 font-sans">
        <button
          onClick={() => { setCode(STARTERS[lang] ?? ""); setOutput(""); setOutputType("idle"); }}
          className="text-xs px-3 py-2 rounded bg-slate-700 text-slate-400 hover:bg-slate-600 transition-colors min-h-[36px]"
        >
          Reset
        </button>
        {onSendToChat && (
          <button
            onClick={() => onSendToChat(code, lang)}
            className="flex-1 text-xs py-2 rounded bg-indigo-600 text-white hover:bg-indigo-500 transition-colors font-medium min-h-[36px]"
          >
            Send to chat →
          </button>
        )}
      </div>
    </div>
  );
}
