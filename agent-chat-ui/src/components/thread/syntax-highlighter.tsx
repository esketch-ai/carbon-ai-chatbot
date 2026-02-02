import { PrismAsyncLight as SyntaxHighlighterPrism } from "react-syntax-highlighter";
import tsx from "react-syntax-highlighter/dist/esm/languages/prism/tsx";
import python from "react-syntax-highlighter/dist/esm/languages/prism/python";
import json from "react-syntax-highlighter/dist/esm/languages/prism/json";
import bash from "react-syntax-highlighter/dist/esm/languages/prism/bash";
import sql from "react-syntax-highlighter/dist/esm/languages/prism/sql";
import css from "react-syntax-highlighter/dist/esm/languages/prism/css";
import markdown from "react-syntax-highlighter/dist/esm/languages/prism/markdown";
import { oneDark } from "react-syntax-highlighter/dist/cjs/styles/prism";
import { FC } from "react";

// Register languages
SyntaxHighlighterPrism.registerLanguage("js", tsx);
SyntaxHighlighterPrism.registerLanguage("javascript", tsx);
SyntaxHighlighterPrism.registerLanguage("jsx", tsx);
SyntaxHighlighterPrism.registerLanguage("ts", tsx);
SyntaxHighlighterPrism.registerLanguage("typescript", tsx);
SyntaxHighlighterPrism.registerLanguage("tsx", tsx);
SyntaxHighlighterPrism.registerLanguage("python", python);
SyntaxHighlighterPrism.registerLanguage("py", python);
SyntaxHighlighterPrism.registerLanguage("json", json);
SyntaxHighlighterPrism.registerLanguage("bash", bash);
SyntaxHighlighterPrism.registerLanguage("sh", bash);
SyntaxHighlighterPrism.registerLanguage("shell", bash);
SyntaxHighlighterPrism.registerLanguage("sql", sql);
SyntaxHighlighterPrism.registerLanguage("css", css);
SyntaxHighlighterPrism.registerLanguage("markdown", markdown);
SyntaxHighlighterPrism.registerLanguage("md", markdown);

// 시각화 언어는 JSON으로 하이라이팅
SyntaxHighlighterPrism.registerLanguage("agchart", json);
SyntaxHighlighterPrism.registerLanguage("aggrid", json);
SyntaxHighlighterPrism.registerLanguage("map", json);
SyntaxHighlighterPrism.registerLanguage("geomap", json);
SyntaxHighlighterPrism.registerLanguage("deckgl", json);

interface SyntaxHighlighterProps {
  children: string;
  language: string;
  className?: string;
}

export const SyntaxHighlighter: FC<SyntaxHighlighterProps> = ({
  children,
  language,
  className,
}) => {
  return (
    <SyntaxHighlighterPrism
      language={language}
      style={oneDark}
      customStyle={{
        margin: 0,
        width: "100%",
        maxWidth: "100%",
        padding: "1.5rem 1rem",
        borderRadius: 0,
        overflowX: "auto",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        overflowWrap: "break-word",
      }}
      className={className}
      wrapLines={true}
      wrapLongLines={true}
    >
      {children}
    </SyntaxHighlighterPrism>
  );
};
