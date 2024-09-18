package util

import "testing"

func TestCoalesce(t *testing.T) {
	t.Run("Empty", func(t *testing.T) {
		result := Coalesce[int]()
		if result != 0 {
			t.Errorf("Expected %v, got %v", 0, result)
		}
	})

	t.Run("Non-empty", func(t *testing.T) {
		result := Coalesce[string]("foo")
		if result != "foo" {
			t.Errorf("Expected %v, got %v", "foo", result)
		}
	})

	t.Run("Multiple non-empty", func(t *testing.T) {
		result := Coalesce[string]("", "foo", "bar")
		if result != "foo" {
			t.Errorf("Expected %v, got %v", "foo", result)
		}
	})

	t.Run("Multiple empty", func(t *testing.T) {
		var zero rune
		result := Coalesce[rune](zero, zero)
		if result != zero {
			t.Errorf("Expected %v, got %v", zero, result)
		}
	})
}
