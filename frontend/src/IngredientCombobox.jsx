import { useEffect, useRef, useState, useMemo } from 'react'

function fuzzyMatch(query, text) {
  let qi = 0
  for (let ti = 0; ti < text.length && qi < query.length; ti++) {
    if (text[ti] === query[qi]) qi++
  }
  return qi === query.length
}

function highlightMatch(name, query) {
  if (!query) return name
  const lower = name.toLowerCase()
  const qLower = query.toLowerCase()
  const idx = lower.indexOf(qLower)
  if (idx !== -1) {
    return (
      <>
        {name.slice(0, idx)}
        <span className="combobox-match">{name.slice(idx, idx + query.length)}</span>
        {name.slice(idx + query.length)}
      </>
    )
  }
  // fuzzy highlight
  const parts = []
  let qi = 0
  for (let i = 0; i < name.length; i++) {
    if (qi < qLower.length && name[i].toLowerCase() === qLower[qi]) {
      parts.push(<span key={i} className="combobox-match">{name[i]}</span>)
      qi++
    } else {
      parts.push(name[i])
    }
  }
  return <>{parts}</>
}

function IngredientCombobox({ ingredients, value, onChange }) {
  const [searchText, setSearchText] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [highlightIndex, setHighlightIndex] = useState(0)
  const wrapperRef = useRef(null)
  const inputRef = useRef(null)
  const listboxRef = useRef(null)

  // Sync searchText when value changes externally (e.g. after addMealItem clears it)
  const selectedIngredient = useMemo(
    () => ingredients.find((i) => i.id === value),
    [ingredients, value],
  )

  // eslint-disable-next-line react-hooks/set-state-in-effect -- syncing derived state from prop
  useEffect(() => {
    setSearchText(selectedIngredient ? selectedIngredient.name : '')
  }, [selectedIngredient])

  const filtered = useMemo(() => {
    const q = searchText.trim().toLowerCase()
    if (!q) return ingredients

    // Substring matches
    const substringMatches = ingredients.filter((i) =>
      i.name.toLowerCase().includes(q),
    )

    if (substringMatches.length > 0) {
      // Sort: starts-with first, then others
      const starts = []
      const rest = []
      for (const item of substringMatches) {
        if (item.name.toLowerCase().startsWith(q)) {
          starts.push(item)
        } else {
          rest.push(item)
        }
      }
      return [...starts, ...rest]
    }

    // Fuzzy fallback
    return ingredients.filter((i) => fuzzyMatch(q, i.name.toLowerCase()))
  }, [ingredients, searchText])

  // eslint-disable-next-line react-hooks/set-state-in-effect -- resetting highlight on filter change
  useEffect(() => {
    setHighlightIndex(0)
  }, [filtered])

  // Scroll highlighted option into view
  useEffect(() => {
    if (!isOpen || !listboxRef.current) return
    const option = listboxRef.current.children[highlightIndex]
    if (option) {
      option.scrollIntoView({ block: 'nearest' })
    }
  }, [highlightIndex, isOpen])

  const selectItem = (item) => {
    onChange(item.id)
    setSearchText(item.name)
    setIsOpen(false)
  }

  const revertText = () => {
    setSearchText(selectedIngredient ? selectedIngredient.name : '')
  }

  const handleInputChange = (e) => {
    const val = e.target.value
    setSearchText(val)
    setIsOpen(true)
    if (value) {
      onChange('')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (!isOpen) {
        setIsOpen(true)
        return
      }
      setHighlightIndex((prev) => (prev + 1) % (filtered.length || 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (!isOpen) {
        setIsOpen(true)
        return
      }
      setHighlightIndex((prev) =>
        prev <= 0 ? (filtered.length || 1) - 1 : prev - 1,
      )
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (isOpen && filtered[highlightIndex]) {
        selectItem(filtered[highlightIndex])
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false)
      revertText()
    } else if (e.key === 'Tab') {
      setIsOpen(false)
    }
  }

  const handleBlur = () => {
    setIsOpen(false)
    revertText()
  }

  const handleFocus = () => {
    setIsOpen(true)
  }

  const handleClear = () => {
    onChange('')
    setSearchText('')
    inputRef.current?.focus()
  }

  const resultCount = filtered.length
  const query = searchText.trim()

  return (
    <div className="combobox-wrapper" ref={wrapperRef}>
      <div className="combobox-input-wrapper">
        <svg
          className="combobox-icon"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          ref={inputRef}
          id="meal-ingredient"
          className="combobox-input"
          role="combobox"
          aria-expanded={isOpen}
          aria-controls="ingredient-listbox"
          aria-autocomplete="list"
          aria-activedescendant={
            isOpen && filtered[highlightIndex]
              ? `ingredient-option-${filtered[highlightIndex].id}`
              : undefined
          }
          autoComplete="off"
          autoCapitalize="off"
          autoCorrect="off"
          value={searchText}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          onFocus={handleFocus}
          placeholder="Search ingredients..."
        />
        {value && (
          <button
            type="button"
            className="combobox-clear"
            onMouseDown={(e) => {
              e.preventDefault()
              handleClear()
            }}
            aria-label="Clear selection"
          >
            &times;
          </button>
        )}
      </div>
      {isOpen && (
        <ul
          id="ingredient-listbox"
          ref={listboxRef}
          role="listbox"
          className="combobox-listbox"
        >
          {filtered.map((item, index) => (
            <li
              key={item.id}
              id={`ingredient-option-${item.id}`}
              role="option"
              aria-selected={highlightIndex === index}
              className={`combobox-option${highlightIndex === index ? ' highlighted' : ''}`}
              onMouseDown={(e) => {
                e.preventDefault()
                selectItem(item)
              }}
              onMouseEnter={() => setHighlightIndex(index)}
            >
              {highlightMatch(item.name, query)}
            </li>
          ))}
          {filtered.length === 0 && query && (
            <li className="combobox-empty">No ingredients match '{query}'</li>
          )}
        </ul>
      )}
      <div className="combobox-sr-only" role="status" aria-live="polite" aria-atomic="true">
        {isOpen ? `${resultCount} result${resultCount !== 1 ? 's' : ''} available` : ''}
      </div>
    </div>
  )
}

export default IngredientCombobox
